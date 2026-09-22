#!/usr/bin/env bash
# Starts a virtual display + noVNC (browser-based VNC viewer) bound to
# localhost only, then opens a visible Chromium at TikTok's login page.
# Meant to be reached through an SSH tunnel, never exposed publicly.
#
# Usage: bash start_vnc_login.sh
# Then from your OWN machine:
#   ssh -L 6080:localhost:6080 -i ~/.ssh/hetzner_ms root@46.62.147.185
#   open http://localhost:6080/vnc.html in your browser, click Connect
set -euo pipefail

APP_DIR="/opt/video-ranking-bot"
DISPLAY_NUM=99
export DISPLAY=":${DISPLAY_NUM}"

echo "== Starting Xvfb on display :${DISPLAY_NUM} =="
pkill -f "Xvfb :${DISPLAY_NUM}" 2>/dev/null || true
Xvfb "${DISPLAY}" -screen 0 1280x900x24 &
sleep 2

echo "== Starting x11vnc (localhost only, port 5900) =="
pkill x11vnc 2>/dev/null || true
VNC_PASS=$(openssl rand -hex 8)
echo "VNC password: ${VNC_PASS}"
x11vnc -display "${DISPLAY}" -localhost -passwd "${VNC_PASS}" -forever -quiet &
sleep 2

echo "== Starting noVNC (localhost only, port 6080) =="
pkill -f websockify 2>/dev/null || true
websockify --web=/usr/share/novnc 127.0.0.1:6080 localhost:5900 &
sleep 2

echo "== Launching Chromium at TikTok login =="
cd "$APP_DIR"
./venv/bin/python deploy/tiktok_login.py
