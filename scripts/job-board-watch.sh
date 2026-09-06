#!/usr/bin/env bash
# Weekly re-qualification of the job boards VJH depends on.
#
# Silent when every board still passes. Sends one Telegram message when a board
# degrades, which is the failure this exists to catch: agentic-engineering-jobs.com
# was rejected on 2026-08-29 because it had stopped posting a month earlier while
# still advertising 1,532 listings and flagging expired roles as fresh. A board
# VJH already trusts can rot the same way, quietly, at any time.
#
# NOTE: does NOT source .env. That file contains values with spaces and angle
# brackets (FROM_EMAIL='Elena Revicheva <aipa [at] aideazz.xyz>') which make
# `. ./.env` a syntax error. Read the two keys we need with grep/cut instead.

set -uo pipefail
cd /home/ubuntu/VibeJobHunterAIPA_AIMCF || exit 2

_env() { grep -E "^${1}=" .env 2>/dev/null | head -1 | cut -d= -f2- | tr -d "\"'" ; }
export TELEGRAM_BOT_TOKEN="$(_env TELEGRAM_BOT_TOKEN)"
export TELEGRAM_CHAT_ID="$(_env TELEGRAM_CHAT_ID)"

echo "=== job-board watch $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
./venv/bin/python scripts/qualify_job_board.py --watch --alert
rc=$?
case $rc in
  0) echo "RESULT: all wired boards still qualified" ;;
  1) echo "RESULT: a wired board FAILED re-qualification (Telegram alert sent)" ;;
  *) echo "RESULT: could not evaluate (rc=$rc)" ;;
esac
exit $rc
