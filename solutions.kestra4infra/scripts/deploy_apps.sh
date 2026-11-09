#!/usr/bin/env bash
# Create or update the catalog apps of apps/ in solutions.kestra4infra (matched on namespace + id).
set -euo pipefail
URL=${KESTRA_URL:-http://localhost:18080}; TENANT=${TENANT:-solutions}; NS=solutions.kestra4infra
AUTH=${KESTRA_AUTH:?set KESTRA_AUTH=user:password}
[ $# -gt 0 ] || set -- apps/*.yaml
existing=$(curl -s -u "$AUTH" "$URL/api/v1/$TENANT/apps/search?size=500")
for f in "$@"; do
  id=$(sed -n 's/^id: *//p' "$f" | head -1)
  uid=$(printf '%s' "$existing" | python3 -c "import sys,json; print(next((a['uid'] for a in json.load(sys.stdin)['results'] if a.get('namespace')=='$NS' and a.get('id')=='$id'), ''))")
  if [ -n "$uid" ]; then m=PUT; u="$URL/api/v1/$TENANT/apps/$uid"; else m=POST; u="$URL/api/v1/$TENANT/apps"; fi
  code=$(curl -s -o /tmp/k4i-app.out -w '%{http_code}' -u "$AUTH" -X $m -H 'Content-Type: application/x-yaml' --data-binary @"$f" "$u")
  if [ "$code" = 200 ]; then echo "ok   $id ($m)"; else echo "FAIL $id ($code): $(head -c 600 /tmp/k4i-app.out)"; fi
done
