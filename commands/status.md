---
description: Check Veto server connection status and active rules
---

Check the Veto configuration at ~/.veto/config.json. If it exists, read the server_url (default: https://api.vetoapp.io), then:

Step 1 - Health check:
Run: `curl -s -o /dev/null -w "%{http_code}" {server_url}/health`

Step 2 - Report: server URL, connection status (ok/unreachable) and fail policy.
