#!/bin/bash
# Review loop: restart the dev server, then screenshot every console route.
cd "$(dirname "$0")"
pkill -f "[v]ite" ; sleep 1
setsid nohup npm run dev -- --port 5175 --strictPort > /tmp/opencode/vite.log 2>&1 < /dev/null &
disown
for i in $(seq 1 25); do
  sleep 1
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5175 --max-time 2)
  [ "$code" = "200" ] && break
done
echo "server: $code"
node qa-shots.mjs http://localhost:5175
