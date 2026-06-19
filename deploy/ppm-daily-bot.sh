#!/usr/bin/env bash
# Локальный cron-runner для PPM Daily Bot.
# Вызывается из crontab пользователя (07:20 МСК ежедневно).
#
# Условия работы:
#  - ноут включен в момент запуска
#  - активен Tailscale с exit-node v2-vpn-kz-01 (нужен для Telegram)
#  - venv проекта собран (.venv/bin/python существует)
set -euo pipefail

PROJECT_DIR="/Users/worker/Documents/Работа в Claude/ppm_analytics"
LOG_DIR="$HOME/Logs/ppm-daily-bot"
LOG="$LOG_DIR/bot.log"

mkdir -p "$LOG_DIR"

# Ротация — если лог > 5 МБ
if [[ -f "$LOG" ]] && (( $(stat -f %z "$LOG") > 5242880 )); then
  mv -f "$LOG_DIR/bot.log.4" "$LOG_DIR/bot.log.5" 2>/dev/null || true
  mv -f "$LOG_DIR/bot.log.3" "$LOG_DIR/bot.log.4" 2>/dev/null || true
  mv -f "$LOG_DIR/bot.log.2" "$LOG_DIR/bot.log.3" 2>/dev/null || true
  mv -f "$LOG_DIR/bot.log.1" "$LOG_DIR/bot.log.2" 2>/dev/null || true
  mv -f "$LOG" "$LOG_DIR/bot.log.1"
fi

cd "$PROJECT_DIR"

{
  echo "=========================================================="
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] starting bot.sender"
  echo "=========================================================="

  # PATH чтобы tailscale и прочее находилось из cron-окружения
  export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

  ./.venv/bin/python -m bot.sender
} >> "$LOG" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] exit code: $?" >> "$LOG"
