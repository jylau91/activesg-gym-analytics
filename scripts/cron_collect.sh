#!/usr/bin/env bash
set -u
PROJECT_DIR="/Users/jy/Projects/activesg-gym-analytics"
START_SGT="2026-06-30T06:00:00+08:00"
END_SGT="2026-07-30T22:00:00+08:00"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/collector.log"
mkdir -p "$LOG_DIR"
cd "$PROJECT_DIR" || exit 1

{
  printf '\n[%s] tick start\n' "$(TZ=Asia/Singapore date '+%Y-%m-%dT%H:%M:%S%z')"
  python3 scripts/collect_once.py \
    --respect-window \
    --start-sgt "$START_SGT" \
    --end-sgt "$END_SGT" \
    --publish \
    --publish-interval-minutes 60
  status=$?
  printf '[%s] tick exit=%s\n' "$(TZ=Asia/Singapore date '+%Y-%m-%dT%H:%M:%S%z')" "$status"
  exit "$status"
} >>"$LOG_FILE" 2>&1

status=$?
if [ "$status" -ne 0 ]; then
  echo "ActiveSG gym analytics collector failed on $(TZ=Asia/Singapore date '+%Y-%m-%d %H:%M:%S %Z'). Last log lines:"
  tail -80 "$LOG_FILE"
  exit "$status"
fi

# Keep stdout empty on success so Hermes no_agent cron remains silent.
exit 0
