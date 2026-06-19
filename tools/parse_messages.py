"""
Парсер исторических сообщений PPM Daily Bot.

Input: data/raw_messages.txt — сырые Telegram-сообщения, склеенные подряд.
Output: data/datamart.json — структурированный датамарт.

Запуск:
    python tools/parse_messages.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw_messages.txt"
OUT = ROOT / "data" / "datamart.json"

MONTHS_RU = {
    "Январь": 1, "Февраль": 2, "Март": 3, "Апрель": 4,
    "Май": 5, "Июнь": 6, "Июль": 7, "Август": 8,
    "Сентябрь": 9, "Октябрь": 10, "Ноябрь": 11, "Декабрь": 12,
}


def num(s: str) -> int:
    """'45 461 537' / '1 138' → 45461537."""
    s = s.replace(" ", "").replace(" ", "").replace("−", "-").replace("−", "-")
    return int(s)


def pct(s: str) -> float:
    """'104,8%' → 1.048."""
    return float(s.replace(",", ".").replace("%", "").strip()) / 100.0


def find_value(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text)
    return m.group(1) if m else None


def parse_plan(text: str, metric_re: str) -> dict | None:
    """
    Парсит строку вида:
        '• GMV: 1 231 970 956 ₽ из 1 350 000 000 ₽ (91,3%) · RR 104,8%'

    metric_re = r'GMV' (имя метрики до двоеточия).
    Возвращает {actual, plan, pct_of_plan, run_rate} либо None.
    """
    pattern = (
        rf"{metric_re}:\s*([\d  ]+?)\s*₽?\s*из\s*"
        rf"([\d  ]+?)\s*₽?\s*\(([\d,]+)%\)\s*·\s*RR\s*([\d,]+)%"
    )
    m = re.search(pattern, text)
    if not m:
        return None
    return {
        "actual": num(m.group(1)),
        "plan": num(m.group(2)),
        "pct_of_plan": pct(m.group(3) + "%"),
        "run_rate": pct(m.group(4) + "%"),
    }


def parse_simple(text: str, metric_re: str) -> int | None:
    m = re.search(rf"{metric_re}:\s*([\d  ]+)\s*₽?", text)
    return num(m.group(1)) if m else None


def parse_days_elapsed(text: str, metric_re: str) -> int | None:
    """'OpEx: −30 724 185 ₽ (за 27 дн.)' → 27."""
    m = re.search(rf"{metric_re}:.*?\(за\s+(\d+)\s+дн\.\)", text)
    return int(m.group(1)) if m else None


def parse_cards_breakdown(text: str) -> dict:
    return {
        "travel": num(re.search(r"Travel:\s*([\d  ]+)", text).group(1)),
        "premium": num(re.search(r"Premium:\s*([\d  ]+)", text).group(1)),
        "subscriptions": num(re.search(r"Subscriptions:\s*([\d  ]+)", text).group(1)),
    }


def parse_gmv_breakdown(text: str) -> dict:
    return {
        "cards_issue": num(re.search(r"за выпуск карт:\s*([\d  ]+)", text).group(1)),
        "topups": num(re.search(r"за пополнения:\s*([\d  ]+)", text).group(1)),
    }


def parse_revenue_breakdown(text: str) -> dict:
    return {
        "cards_issue": num(re.search(r"с открытия карт:\s*([\d  ]+)", text).group(1)),
        "topups": num(re.search(r"с пополнений:\s*([\d  ]+)", text).group(1)),
    }


def parse_gp_breakdown(text: str) -> dict:
    out = {}
    if m := re.search(r"GP с открытия карт:\s*([\d  ]+)", text):
        out["cards_issue"] = num(m.group(1))
    if m := re.search(r"GP с пополнений:\s*([\d  ]+)", text):
        out["topups"] = num(m.group(1))
    if m := re.search(r"OpEx:\s*[−\-]([\d  ]+)", text):
        out["opex"] = -num(m.group(1))
    if m := re.search(r"ComEx:\s*[−\-]([\d  ]+)", text):
        out["comex"] = -num(m.group(1))
    return out


def parse_daily_section(text: str) -> dict:
    new_clients = num(re.search(r"Новых клиентов:\s*([\d  ]+)", text).group(1))
    new_cards_total = num(re.search(r"Новых карт:\s*([\d  ]+)", text).group(1))
    return {
        "new_clients": new_clients,
        "new_cards": {"total": new_cards_total, **parse_cards_breakdown(text)},
        "gmv": {"total": parse_simple(text, "GMV"), **parse_gmv_breakdown(text)},
        "revenue": {"total": parse_simple(text, "Revenue"), **parse_revenue_breakdown(text)},
        "gross_profit": {"total": parse_simple(text, "Gross Profit"), **parse_gp_breakdown(text)},
        "net_profit": parse_simple(text, "Чистая прибыль"),
    }


def parse_period_section(text: str, label: str) -> dict:
    days_elapsed = parse_days_elapsed(text, "OpEx") or parse_days_elapsed(text, "ComEx")
    period = {
        "label": label,
        "new_clients": parse_plan(text, "Новых клиентов"),
        "new_cards": {
            **(parse_plan(text, "Новых карт") or {}),
            **parse_cards_breakdown(text),
        },
        "gmv": {**(parse_plan(text, "GMV") or {}), **parse_gmv_breakdown(text)},
        "revenue": {
            "actual": parse_simple(text, "Revenue"),
            **parse_revenue_breakdown(text),
        },
        "gross_profit": {**(parse_plan(text, "Gross Profit") or {}), **parse_gp_breakdown(text)},
        "net_profit": parse_plan(text, "Чистая прибыль"),
        "days_elapsed": days_elapsed,
    }
    return period


def split_into_days(raw: str) -> list[tuple[str, str]]:
    """Возвращает [(DD.MM.YYYY, block_text), ...]."""
    pattern = r"Ежедневная сводка ППМ\s*—\s*(\d{2}\.\d{2}\.\d{4})"
    matches = list(re.finditer(pattern, raw))
    out = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        out.append((m.group(1), raw[start:end]))
    return out


def split_block_by_period(block: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Делит block на (daily_text, [(period_label, period_text), ...]).
    Период начинается с '📊 За …'.
    """
    sep = re.compile(r"📊\s*За\s+([^\n]+)\n")
    parts = list(sep.finditer(block))
    if not parts:
        return block, []
    daily_text = block[: parts[0].start()]
    periods = []
    for i, m in enumerate(parts):
        start = m.end()
        end = parts[i + 1].start() if i + 1 < len(parts) else len(block)
        label = m.group(1).strip()
        periods.append((label, block[start:end]))
    return daily_text, periods


def iso_date(ddmmyyyy: str) -> str:
    d, m, y = ddmmyyyy.split(".")
    return f"{y}-{m}-{d}"


def main() -> int:
    raw = RAW.read_text(encoding="utf-8")
    days = split_into_days(raw)
    if not days:
        print("ERROR: no daily messages found", file=sys.stderr)
        return 1

    out_days = []
    for date_str, block in days:
        daily_text, periods = split_block_by_period(block)
        day = {
            "date": iso_date(date_str),
            "daily": parse_daily_section(daily_text),
            "month": None,
            "quarter": None,
        }
        for label, ptext in periods:
            section = parse_period_section(ptext, label)
            if label.startswith("Q"):
                day["quarter"] = section
            else:
                day["month"] = section
        out_days.append(day)

    datamart = {
        "schema_version": 1,
        "source": "Telegram bot daily summaries archive",
        "period": {
            "from": out_days[0]["date"],
            "to": out_days[-1]["date"],
            "days_count": len(out_days),
        },
        "days": out_days,
    }
    OUT.write_text(json.dumps(datamart, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: {len(out_days)} days → {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
