#!/usr/bin/env bash
# One-time setup for running the pipeline on a Hetzner VPS via cron
# instead of GitHub Actions (GitHub's runner IPs are blocked by YouTube's
# bot-check; this dedicated small VPS has a much less-abused IP).
#
# Run as root (or with sudo) on a fresh Ubuntu/Debian Hetzner box:
#   bash hetzner_setup.sh
set -euo pipefail

REPO_URL="https://github.com/oceanfarm1992-design/video-ranking-bot.git"
APP_DIR="/opt/video-ranking-bot"

echo "== Installing system dependencies =="
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg git

echo "== Adding a 4GB swapfile (RAM is tight for torch/Demucs + MoviePy) =="
if [ ! -f /swapfile ]; then
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== Cloning repo =="
if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "== Creating virtualenv and installing dependencies =="
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "== Next steps =="
echo "1. Copy your local .env into $APP_DIR/.env (scp it over, or paste with nano)."
echo "2. If using TikTok fetching, also copy tiktok_cookies.txt into $APP_DIR/."
echo "3. Install the crontab: crontab $APP_DIR/deploy/crontab.txt"
echo "4. Test manually first: cd $APP_DIR && ./venv/bin/python main.py"
