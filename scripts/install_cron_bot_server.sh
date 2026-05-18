#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/ai-invest-simulator"
WEB_HTML="/var/www/html/simulator.html"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# Server cron runs in UTC. These UTC times map to:
# KR: 08:00 UTC = 17:00 KST, Monday-Friday
# US: 22:00 UTC = 07:00 KST next day, Monday-Friday UTC = Tuesday-Saturday KST
KR_CRON_LINE="0 8 * * 1-5 cd $PROJECT_DIR && ./venv/bin/python -m app.cli run --market KR >> $LOG_DIR/daily.log 2>&1 && sudo cp reports/simulator.html $WEB_HTML"
US_CRON_LINE="0 22 * * 1-5 cd $PROJECT_DIR && ./venv/bin/python -m app.cli run --market US >> $LOG_DIR/daily.log 2>&1 && sudo cp reports/simulator.html $WEB_HTML"
(crontab -l 2>/dev/null | grep -v "ai-invest-simulator" | grep -v "CRON_TZ=Asia/Seoul"; echo "$KR_CRON_LINE"; echo "$US_CRON_LINE") | crontab -
