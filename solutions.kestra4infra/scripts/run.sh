#!/usr/bin/env bash
# run.sh <flowId> [key=value ...]: start a flow of solutions.kestra4infra, wait, print the task states.
set -euo pipefail
URL=${KESTRA_URL:-http://localhost:18080}; TENANT=${TENANT:-solutions}; NS=solutions.kestra4infra
AUTH=${KESTRA_AUTH:?set KESTRA_AUTH=user:password}
flow=$1; shift; args=(); for kv in "$@"; do args+=(-F "$kv"); done
curl -s -u "$AUTH" -X POST "${args[@]}" "$URL/api/v1/$TENANT/executions/$NS/$flow?wait=true" | python3 -c '
import sys, json
d = json.load(sys.stdin)
if "id" not in d: print(d); sys.exit(1)
print(d["id"], d["state"]["current"])
for t in d.get("taskRunList") or []:
    if t["state"]["current"] != "SUCCESS": print("  ", t["taskId"], t["state"]["current"])'
