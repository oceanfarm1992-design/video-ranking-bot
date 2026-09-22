#!/usr/bin/env bash
# One-time setup for the Hetzner VPS. This box only does fetch + rank +
# download (yt-dlp works fine from here, unlike GitHub's runner IPs
# which YouTube blocks) and publishes a clips-* GitHub release. The
# heavy processing (Demucs, MoviePy) and Buffer post happen in GitHub
# Actions, triggered automatically by that release - so no torch/
# Demucs/MoviePy needed on this VPS at all.
#
# Run as root on a fresh Ubuntu/Debian Hetzner box:
#   bash hetzner_setup.sh
set -euo pipefail

REPO_URL="https://github.com/oceanfarm1992-design/video-ranking-bot.git"
APP_DIR="/opt/video-ranking-bot"

echo "== Installing system dependencies =="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg git

echo "== Cloning repo =="
if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "== Creating virtualenv and installing lightweight dependencies =="
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements-hetzner.txt

echo "== Next steps =="
echo "1. Copy your .env into $APP_DIR/.env (needs YOUTUBE_API_KEY and GITHUB_TOKEN"
echo "   with repo scope, so this box can publish the clips-* release)."
echo "2. If using TikTok fetching, also copy tiktok_cookies.txt into $APP_DIR/."
echo "3. Install the crontab: crontab $APP_DIR/deploy/crontab.txt"
echo "4. Test manually first: cd $APP_DIR && ./venv/bin/python fetch_download.py"
