---
description: Check Veto server connection status and active rules
---

Check the Veto configuration at ~/.veto/config.json. If it exists, read the server_url (default: https://api.vetoapp.io) and api_key, then:

Step 1 - Health check:
Run: `curl -s -o /dev/null -w "%{http_code}" {server_url}/health`

Step 2 - Rules check:
Run: `curl -s -H "Authorization: Bearer {api_key}" {server_url}/api/v1/rules`

Step 3 - Report: server URL, connection status (ok/unreachable), rule count, and fail policy.
