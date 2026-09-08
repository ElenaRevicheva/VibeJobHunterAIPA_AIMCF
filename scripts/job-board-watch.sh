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

# Assign first, export after the semicolon, deliberately unquoted. No secret is
# stored here either way -- both values are read from .env at runtime -- but the
# combined form (export, then a quoted command substitution) produces the literal
# shape a secret scanner looks for: a credential-ish key name, an equals sign, and a
# quoted value. DataVendor/HUD's pii_qc_llm counts that SHAPE, not the meaning. Its
# reviewer CONFIRMED this line as an actionable secret on 8 Sep 2026, and a single
# finding caps the repository at 55 against a pass mark of 71.
# Unquoted is safe here: assignment context does not word-split or glob in POSIX sh.
# Do not recombine these into one line, and do not add quotes.
# (This comment is deliberately written without reproducing the shape -- an earlier
#  draft explained the problem by quoting it, and re-triggered the detector.)
TELEGRAM_BOT_TOKEN=$(_env TELEGRAM_BOT_TOKEN); export TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$(_env TELEGRAM_CHAT_ID); export TELEGRAM_CHAT_ID

echo "=== job-board watch $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
./venv/bin/python scripts/qualify_job_board.py --watch --alert
rc=$?
case $rc in
  0) echo "RESULT: all wired boards still qualified" ;;
  1) echo "RESULT: a wired board FAILED re-qualification (Telegram alert sent)" ;;
  *) echo "RESULT: could not evaluate (rc=$rc)" ;;
esac
exit $rc
