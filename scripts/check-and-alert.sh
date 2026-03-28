#!/usr/bin/env bash
# check-and-alert.sh — Claude usage threshold checker for OpenClaw cron
# Exits 0 if all metrics are below 70%, 1 if any exceed it.

THRESHOLD=70
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Run claude-usage --json, try npx tsx fallback if not globally installed
if command -v claude-usage &>/dev/null; then
  JSON=$(claude-usage --json 2>&1)
else
  JSON=$(cd "$PROJECT_DIR" && npx tsx src/index.ts --json 2>&1)
fi

EXIT_CODE=$?
if [ $EXIT_CODE -eq 2 ]; then
  echo "ERROR: claude-usage failed to fetch data"
  echo "$JSON"
  exit 2
fi

# Parse metrics with python3 (always available on macOS)
read -r SESSION WEEKLY SONNET MAX <<< "$(echo "$JSON" | python3 -c "
import sys, json
d = json.load(sys.stdin)
s = d.get('session_pct', 0)
w = d.get('weekly_pct', 0)
n = d.get('sonnet_pct', 0)
m = max(s, w, n)
print(s, w, n, m)
")"

ALERT=0
MESSAGES=()

if [ "$SESSION" -ge "$THRESHOLD" ]; then
  MESSAGES+=("⏱  Session (5h): ${SESSION}%")
  ALERT=1
fi

if [ "$WEEKLY" -ge "$THRESHOLD" ]; then
  MESSAGES+=("📊 Weekly (All): ${WEEKLY}%")
  ALERT=1
fi

if [ "$SONNET" -ge "$THRESHOLD" ]; then
  MESSAGES+=("🎯 Sonnet Only:  ${SONNET}%")
  ALERT=1
fi

if [ "$ALERT" -eq 1 ]; then
  echo "⚠️  Claude usage alert — threshold ${THRESHOLD}% exceeded:"
  for msg in "${MESSAGES[@]}"; do
    echo "   $msg"
  done
  echo ""
  echo "Run \`claude-usage\` for full details."
  exit 1
else
  echo "✓ Claude usage OK — Session: ${SESSION}%, Weekly: ${WEEKLY}%, Sonnet: ${SONNET}% (all below ${THRESHOLD}%)"
  exit 0
fi
