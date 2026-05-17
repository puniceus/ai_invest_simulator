#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/home/ubuntu/ai-invest-simulator"
WEB_HTML="/var/www/html/simulator.html"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

CRON_TZ_LINE="CRON_TZ=Asia/Seoul"
KR_CRON_LINE="0 17 * * 1-5 cd $PROJECT_DIR && ./venv/bin/python -m app.cli run --market KR >> $LOG_DIR/daily.log 2>&1 && cp reports/simulator.html $WEB_HTML"
US_CRON_LINE="0 7 * * 2-6 cd $PROJECT_DIR && ./venv/bin/python -m app.cli run --market US >> $LOG_DIR/daily.log 2>&1 && cp reports/simulator.html $WEB_HTML"
(crontab -l 2>/dev/null | grep -v "ai-invest-simulator" | grep -v "CRON_TZ=Asia/Seoul"; echo "$CRON_TZ_LINE"; echo "$KR_CRON_LINE"; echo "$US_CRON_LINE") | crontab -
