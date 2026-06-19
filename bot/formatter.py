"""
Форматирование сводки в текст Telegram-сообщения.

Контракт совпадает 1:1 с историческими сообщениями бота (data/raw_messages.txt).
"""
from __future__ import annotations

from datetime import date

NBSP = " "
SEP = "───────────────"


def fmt_int(n: int) -> str:
    s = f"{abs(int(n)):,}".replace(",", NBSP)
    return ("−" + s) if n < 0 else s


def fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def _plan_tail(p: dict, with_rub: bool = False) -> str:
    if not p or p.get("plan") is None:
        return ""
    rub = f"{NBSP}₽" if with_rub else ""
    return (
        f" из {fmt_int(p['plan'])}{rub}"
        f" ({fmt_pct(p['pct_of_plan'])})"
        f" · RR {fmt_pct(p['run_rate'])}"
    )


def _format_daily(d: dict, header: str) -> list[str]:
    out = [header, ""]
    dly = d["daily"]
    out.append(f"• Новых клиентов: {fmt_int(dly['new_clients'])}")
    out.append(f"• Новых карт: {fmt_int(dly['new_cards']['total'])}")
    out.append(f"   – Travel: {fmt_int(dly['new_cards']['travel'])}")
    out.append(f"   – Premium: {fmt_int(dly['new_cards']['premium'])}")
    out.append(f"   – Subscriptions: {fmt_int(dly['new_cards']['subscriptions'])}")
    out.append("")
    out.append(f"• GMV: {fmt_int(dly['gmv']['total'])}{NBSP}₽")
    out.append(f"   – за выпуск карт: {fmt_int(dly['gmv']['cards_issue'])}{NBSP}₽")
    out.append(f"   – за пополнения: {fmt_int(dly['gmv']['topups'])}{NBSP}₽")
    out.append("")
    out.append(f"• Revenue: {fmt_int(dly['revenue']['total'])}{NBSP}₽")
    out.append(f"   – с открытия карт: {fmt_int(dly['revenue']['cards_issue'])}{NBSP}₽")
    out.append(f"   – с пополнений: {fmt_int(dly['revenue']['topups'])}{NBSP}₽")
    out.append("")
    gp = dly["gross_profit"]
    out.append(f"• Gross Profit: {fmt_int(gp['total'])}{NBSP}₽")
    if "cards_issue" in gp:
        out.append(f"   – GP с открытия карт: {fmt_int(gp['cards_issue'])}{NBSP}₽")
    if "topups" in gp:
        out.append(f"   – GP с пополнений: {fmt_int(gp['topups'])}{NBSP}₽")
    out.append(f"   – OpEx: {fmt_int(gp['opex'])}{NBSP}₽")
    out.append(f"   – ComEx: {fmt_int(gp['comex'])}{NBSP}₽")
    out.append("")
    out.append(f"• Чистая прибыль: {fmt_int(dly['net_profit'])}{NBSP}₽")
    return out


def _format_period(p: dict) -> list[str]:
    out = ["", SEP, "", f"📊 За {p['label']}", ""]
    nc = p["new_clients"]
    out.append(f"• Новых клиентов: {fmt_int(nc['actual'])}{_plan_tail(nc)}")
    cards = p["new_cards"]
    out.append(f"• Новых карт: {fmt_int(cards['actual'])}{_plan_tail(cards)}")
    out.append(f"   – Travel: {fmt_int(cards['travel'])}")
    out.append(f"   – Premium: {fmt_int(cards['premium'])}")
    out.append(f"   – Subscriptions: {fmt_int(cards['subscriptions'])}")
    out.append("")
    gmv = p["gmv"]
    out.append(f"• GMV: {fmt_int(gmv['actual'])}{NBSP}₽{_plan_tail(gmv, with_rub=True)}")
    out.append(f"   – за выпуск карт: {fmt_int(gmv['cards_issue'])}{NBSP}₽")
    out.append(f"   – за пополнения: {fmt_int(gmv['topups'])}{NBSP}₽")
    out.append("")
    rev = p["revenue"]
    out.append(f"• Revenue: {fmt_int(rev['actual'])}{NBSP}₽")
    out.append(f"   – с открытия карт: {fmt_int(rev['cards_issue'])}{NBSP}₽")
    out.append(f"   – с пополнений: {fmt_int(rev['topups'])}{NBSP}₽")
    out.append("")
    gp = p["gross_profit"]
    out.append(f"• Gross Profit: {fmt_int(gp['actual'])}{NBSP}₽{_plan_tail(gp, with_rub=True)}")
    if "cards_issue" in gp:
        out.append(f"   – GP с открытия карт: {fmt_int(gp['cards_issue'])}{NBSP}₽")
    if "topups" in gp:
        out.append(f"   – GP с пополнений: {fmt_int(gp['topups'])}{NBSP}₽")
    days = p.get("days_elapsed")
    days_tail = f" (за {days}{NBSP}дн.)" if days else ""
    out.append(f"   – OpEx: {fmt_int(gp['opex'])}{NBSP}₽{days_tail}")
    out.append(f"   – ComEx: {fmt_int(gp['comex'])}{NBSP}₽{days_tail}")
    out.append("")
    np_ = p["net_profit"]
    out.append(f"• Чистая прибыль: {fmt_int(np_['actual'])}{NBSP}₽{_plan_tail(np_, with_rub=True)}")
    return out


def format_summary(day: dict) -> str:
    d = date.fromisoformat(day["date"])
    header = f"Ежедневная сводка ППМ — {d.strftime('%d.%m.%Y')}"
    lines = _format_daily(day, header)
    if day.get("month"):
        lines += _format_period(day["month"])
    if day.get("quarter"):
        lines += _format_period(day["quarter"])
    return "\n".join(lines)
