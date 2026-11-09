#!/usr/bin/env bash
# Create or update the flows of flows/ in solutions.kestra4infra on the local instance.
set -euo pipefail
URL=${KESTRA_URL:-http://localhost:18080}; TENANT=${TENANT:-solutions}; NS=solutions.kestra4infra
AUTH=${KESTRA_AUTH:?set KESTRA_AUTH=user:password}
[ $# -gt 0 ] || set -- flows/*.yaml
for f in "$@"; do
  id=$(sed -n 's/^id: *//p' "$f" | head -1)
  code=$(curl -s -o /tmp/k4i-deploy.out -w '%{http_code}' -u "$AUTH" "$URL/api/v1/$TENANT/flows/$NS/$id")
  if [ "$code" = 200 ]; then m=PUT; u="$URL/api/v1/$TENANT/flows/$NS/$id"; else m=POST; u="$URL/api/v1/$TENANT/flows"; fi
  code=$(curl -s -o /tmp/k4i-deploy.out -w '%{http_code}' -u "$AUTH" -X $m -H 'Content-Type: application/x-yaml' --data-binary @"$f" "$u")
  if [ "$code" = 200 ]; then echo "ok   $id"; else echo "FAIL $id ($code): $(head -c 600 /tmp/k4i-deploy.out)"; fi
done
