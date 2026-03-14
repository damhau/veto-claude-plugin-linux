#!/usr/bin/env python3
"""
Veto hook script: evaluates tool calls against the Veto server.

Reads the hook input from stdin, sends it to the Veto API for evaluation,
and outputs the decision (allow/deny) to stdout. Falls back to the configured
fail policy (open or closed) if the server is unreachable.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
import ssl

CONFIG_PATH = os.path.expanduser("~/.veto/config.json")
LOG_PATH = os.path.expanduser("~/.veto/hook.log")


def log(msg):
    try:
        ts = datetime.now(timezone.utc).isoformat()
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass  # never break execution because of logging


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log(f"load_config failed: {e}")
        return None


def send_decision(decision):
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {"behavior": decision},
                }
            }
        )
    )


def build_ssl_context(config):
    verify_ssl = config.get("verify_ssl", True)
    ca_file = config.get("ca_file", None)

    if not verify_ssl:
        log("SSL verification disabled")
        return ssl._create_unverified_context()

    try:
        if ca_file:
            log(f"SSL verification enabled with custom CA file: {ca_file}")
            return ssl.create_default_context(cafile=ca_file)

        log("SSL verification enabled with system CA store")
        return ssl.create_default_context()
    except Exception as e:
        log(f"failed to build SSL context: {e}")
        return None


def main():
    log("start")

    # Read hook input safely
    try:
        hook_input = json.load(sys.stdin)
        log(
            f"hook_input: session={hook_input.get('session_id')} tool={hook_input.get('tool_name')}"
        )
    except Exception as e:
        log(f"failed to read stdin: {e}")
        sys.exit(0)

    config = load_config()
    if not config:
        log("missing config -> fail open")
        sys.exit(0)

    server_url = config.get("server_url", "https://api.vetoapp.io")
    api_key = config.get("api_key", "")
    fail_policy = config.get("fail_policy", "open")
    timeout = config.get("timeout", 25)

    ssl_context = build_ssl_context(config)
    if ssl_context is None:
        log("invalid SSL configuration")

        if fail_policy == "closed":
            log("fail_policy=closed -> deny")
            send_decision("deny")

        sys.exit(0)

    payload_dict = {
        "session_id": hook_input.get("session_id", "unknown"),
        "tool_name": hook_input.get("tool_name", ""),
        "tool_input": hook_input.get("tool_input", {}),
        "cwd": hook_input.get("cwd"),
        "permission_mode": hook_input.get("permission_mode"),
        "hook_event_name": hook_input.get("hook_event_name"),
        "raw_hook": hook_input,
    }

    payload = json.dumps(payload_dict).encode()

    log(f"sending request to {server_url}")

    try:
        req = urllib.request.Request(
            f"{server_url}/api/v1/hooks/evaluate",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            result = json.loads(resp.read())
            log(f"response: {result}")

    except Exception as e:
        log(f"request failed: {e}")

        if fail_policy == "closed":
            log("fail_policy=closed -> deny")
            send_decision("deny")

        sys.exit(0)

    decision = result.get("decision", "ask")
    log(f"decision: {decision}")

    if decision == "allow":
        send_decision("allow")
    elif decision == "deny":
        send_decision("deny")
    else:
        # ask -> no output, Claude will prompt user
        log("decision=ask -> no output")

    sys.exit(0)


if __name__ == "__main__":
    main()
