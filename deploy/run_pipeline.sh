#!/usr/bin/env bash
# Wrapper invoked by cron: activates the venv, fetches+ranks+downloads,
# and publishes a clips-* GitHub release. GitHub Actions picks it up
# from there (Demucs, MoviePy, Buffer post). Logs with a timestamp so
# failures are visible after the fact.
set -euo pipefail

APP_DIR="/opt/video-ranking-bot"
LOG_DIR="$APP_DIR/logs"
mkdir -p "$LOG_DIR"

cd "$APP_DIR"
git pull --ff-only

STAMP=$(date -u +%Y%m%d-%H%M%S)
./venv/bin/python fetch_download.py >> "$LOG_DIR/run-$STAMP.log" 2>&1

# Keep only the last 30 log files
ls -1t "$LOG_DIR"/run-*.log 2>/dev/null | tail -n +31 | xargs -r rm --
