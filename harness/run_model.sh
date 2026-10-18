#!/usr/bin/env bash
# Usage: harness/run_model.sh <name>   (name is a key in harness/endpoints.json)
# Waits for the vLLM server, runs one smoke video, then the full eval.
set -u
cd "$(dirname "$0")/.."
NAME="$1"
REPEATS="${RUN_REPEATS:-10}"
RUN_TEMP="${RUN_TEMPERATURE:-0.6}"
CONC="${RUN_CONCURRENCY:-8}"

read -r URL THINK SYS_IN_USER < <(python -c "
import json,sys
e=json.load(open('harness/endpoints.json'))['$NAME']
print(e['url'], 1 if e['thinking_toggle'] else 0, 1 if e.get('system_in_user') else 0)")

export VLM_BASE_URL="$URL"
export VLM_MODEL="$NAME"
export VLM_API_KEY="$(cut -d' ' -f2 harness/.vlm_key)"
export DISABLE_THINKING="$THINK"
export SYSTEM_IN_USER="$SYS_IN_USER"
export PYTHONIOENCODING=utf-8

RUN_NAME="$NAME${RUN_SUFFIX:-}"
LOG="harness/runs/$RUN_NAME.log"
mkdir -p harness/runs
# wait for a previous eval on the same server (e.g. the v1 run) to finish first
while [ -n "${WAIT_FOR:-}" ] && [ ! -f "harness/runs/$NAME/summary.json" ]; do sleep 30; done
echo "$(date +%H:%M:%S) waiting for $URL" >> "$LOG"
until curl -sf -m 10 -H "Authorization: Bearer $VLM_API_KEY" "$URL/models" > /dev/null; do
  sleep 20
done
if [ -z "${RUN_SUFFIX:-}" ]; then
  echo "$(date +%H:%M:%S) server up, smoke" >> "$LOG"
  python harness/smoke.py open/videos/X-1.mov >> "$LOG" 2>&1
fi
echo "$(date +%H:%M:%S) eval start repeats=$REPEATS temp=$RUN_TEMP conc=$CONC" >> "$LOG"
python harness/eval.py --name "$RUN_NAME" --repeats "$REPEATS" --temperature "$RUN_TEMP" --concurrency "$CONC" >> "$LOG" 2>&1
echo "$(date +%H:%M:%S) DONE" >> "$LOG"
