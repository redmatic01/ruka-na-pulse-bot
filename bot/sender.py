"""
Entry-point: формирует сводку за дату и отправляет в Telegram.

Запуск:
    python -m bot.sender                 # вчерашняя дата
    python -m bot.sender 2026-06-03      # конкретная
    python -m bot.sender 2026-06-03 --dry-run   # печать в stdout, без TG
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from bot import datamart
from bot.formatter import format_summary


def _load_env() -> None:
    """Минимальный .env-loader (без зависимости от python-dotenv)."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _send_telegram(text: str) -> None:
    import urllib.parse
    import urllib.request

    token = os.environ["BOT_TOKEN"]
    chat_ids = [c.strip() for c in os.environ["CHAT_IDS"].split(",") if c.strip()]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    for chat_id in chat_ids:
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="PPM Daily Bot — sender")
    p.add_argument("target_date", nargs="?", help="YYYY-MM-DD (default: вчера)")
    p.add_argument("--dry-run", action="store_true", help="вывод в stdout, не отправлять в TG")
    args = p.parse_args(argv)

    if args.target_date:
        d = date.fromisoformat(args.target_date)
    else:
        d = date.today() - timedelta(days=1)

    day = datamart.get_day(d)
    text = format_summary(day)

    if args.dry_run:
        print(text)
        return 0

    _load_env()
    if "BOT_TOKEN" not in os.environ:
        print("ERROR: BOT_TOKEN не задан. Используй --dry-run для smoke-test.", file=sys.stderr)
        return 2
    _send_telegram(text)
    print(f"sent for {d.isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
