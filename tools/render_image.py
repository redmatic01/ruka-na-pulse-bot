"""
Рендерит PNG-картинку дневного отчёта ППМ из одного дня датамарта.

Архитектура зеркалит прод: HTML-шаблон → Playwright headless Chromium → screenshot.

Запуск:
    python tools/render_image.py 2026-06-03
    python tools/render_image.py 2026-06-18 --out data/images/2026-06-18.png
    python tools/render_image.py 2026-06-03 --datamart data/datamart.json

Требования:
    pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "templates" / "daily_report.html"

MONTHS_NOM = {
    1: "ЯНВАРЬ", 2: "ФЕВРАЛЬ", 3: "МАРТ", 4: "АПРЕЛЬ",
    5: "МАЙ", 6: "ИЮНЬ", 7: "ИЮЛЬ", 8: "АВГУСТ",
    9: "СЕНТЯБРЬ", 10: "ОКТЯБРЬ", 11: "НОЯБРЬ", 12: "ДЕКАБРЬ",
}
ROMAN_Q = {1: "I", 2: "II", 3: "III", 4: "IV"}

# SVG-иконки в outline-стиле (feather-like) — цвет наследуется от .icon (--green).
SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
    'stroke-linecap="round" stroke-linejoin="round">{}</svg>'
)
ICON_USER  = SVG.format('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle>')
ICON_CARD  = SVG.format('<rect x="3" y="5" width="18" height="14" rx="2"></rect><line x1="3" y1="10" x2="21" y2="10"></line>')
ICON_COIN  = SVG.format('<circle cx="12" cy="12" r="9"></circle><path d="M9.5 9.5h4a2 2 0 0 1 0 4h-4v-4z"></path><path d="M9.5 13.5h4.5a2 2 0 0 1 0 4h-4.5v-4z"></path>')
ICON_CHART = SVG.format('<polyline points="3 17 9 11 13 15 21 7"></polyline><polyline points="14 7 21 7 21 14"></polyline>')
ICON_GEM   = SVG.format('<path d="M6 3h12l4 6-10 12L2 9l4-6z"></path><path d="M11 3 8 9l4 12 4-12-3-6"></path><line x1="2" y1="9" x2="22" y2="9"></line>')

METRIC_ROWS = [
    {"key": "new_clients", "label": "Новые клиенты",                "icon": ICON_USER,  "unit": "int"},
    {"key": "new_cards",   "label": "Новые карты",                  "icon": ICON_CARD,  "unit": "int"},
    {"key": "gmv",         "label": "GMV, млн руб.",                "icon": ICON_COIN,  "unit": "mln"},
    {"key": "gross_profit","label": "Gross Profit,<br>млн руб.",    "icon": ICON_CHART, "unit": "mln"},
    {"key": "net_profit",  "label": "Net Profit,<br>млн руб.",      "icon": ICON_GEM,   "unit": "mln"},
]


# ────────────────────────── форматтеры ──────────────────────────

NBSP = " "  # thin space в HTML; даём nbsp чтобы разряды не переносились


def fmt_int(n: int | float) -> str:
    n = int(round(n))
    s = f"{abs(n):,}".replace(",", NBSP)
    return ("−" + s) if n < 0 else s


def fmt_mln(n: int | float) -> str:
    """45 461 537 → '45,5'."""
    v = n / 1_000_000
    return f"{v:,.1f}".replace(",", NBSP).replace(".", ",")


def fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def fmt_pct1(x: float) -> str:
    return f"{x * 100:.1f}".replace(".", ",") + "%"


def ru_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def month_label(month_dict: dict, iso: str) -> str:
    mm = int(iso.split("-")[1])
    return MONTHS_NOM[mm]


def quarter_label(quarter_dict: dict) -> str:
    # 'Q2 2026' → 'II КВАРТАЛ'
    label = quarter_dict.get("label", "")
    if label.startswith("Q") and len(label) > 1:
        q_num = int(label[1])
        return f"{ROMAN_Q[q_num]} КВАРТАЛ"
    return label.upper()


# ────────────────────────── ячейки ──────────────────────────

def day_value(day_daily: dict, key: str, unit: str) -> int | float:
    if key == "new_clients":   return day_daily["new_clients"]
    if key == "new_cards":     return day_daily["new_cards"]["total"]
    if key == "gmv":           return day_daily["gmv"]["total"]
    if key == "gross_profit":  return day_daily["gross_profit"]["total"]
    if key == "net_profit":    return day_daily["net_profit"]
    raise KeyError(key)


def period_block(period: dict, key: str, unit: str) -> dict | None:
    if not period:
        return None
    metric = period.get(key)
    if not metric:
        return None
    if key == "new_clients":
        actual, plan = metric["actual"], metric.get("plan")
        rr = metric.get("run_rate")
        pct_plan = metric.get("pct_of_plan")
    elif key == "new_cards":
        actual, plan = metric["actual"], metric.get("plan")
        rr = metric.get("run_rate")
        pct_plan = metric.get("pct_of_plan")
    elif key == "gmv":
        actual, plan = metric["actual"], metric.get("plan")
        rr = metric.get("run_rate")
        pct_plan = metric.get("pct_of_plan")
    elif key == "gross_profit":
        actual, plan = metric["actual"], metric.get("plan")
        rr = metric.get("run_rate")
        pct_plan = metric.get("pct_of_plan")
    elif key == "net_profit":
        actual, plan = metric["actual"], metric.get("plan")
        rr = metric.get("run_rate")
        pct_plan = metric.get("pct_of_plan")
    else:
        return None
    return {"actual": actual, "plan": plan, "rr": rr, "pct_of_plan": pct_plan}


def render_period_cell(blk: dict | None, unit: str) -> str:
    if blk is None:
        return '<td class="period"></td>'
    actual = blk["actual"]; plan = blk["plan"]; rr = blk["rr"]; pct = blk["pct_of_plan"]
    fmt = fmt_mln if unit == "mln" else fmt_int
    actual_s = fmt(actual)
    plan_s = (fmt(plan) + (" млн&nbsp;руб." if unit == "mln" else "")) if plan is not None else ""
    pct_s = fmt_pct(pct) if pct is not None else ""
    rr_dir = "up" if (rr is not None and rr >= 1.0) else "down"
    rr_arrow = "↑" if rr_dir == "up" else "↓"
    rr_s = f"RR&nbsp;{fmt_pct1(rr)}&nbsp;{rr_arrow}" if rr is not None else ""
    bar_width = max(0.0, min(1.0, pct or 0.0)) * 100
    bar_class = "" if rr_dir == "up" else "red"
    return f"""<td class="period">
      <div class="top">
        <div class="num">{actual_s}</div>
        <div class="pct">{pct_s}</div>
      </div>
      <div class="plan">из {plan_s}</div>
      <div class="rr {rr_dir}">{rr_s}</div>
      <div class="bar"><div class="{bar_class}" style="width:{bar_width:.1f}%"></div></div>
    </td>"""


def render_row(metric: dict, day_dict: dict) -> str:
    key = metric["key"]; unit = metric["unit"]
    daily = day_dict["daily"]
    month = day_dict.get("month") or {}
    quarter = day_dict.get("quarter") or {}

    fmt = fmt_mln if unit == "mln" else fmt_int
    day_val_s = fmt(day_value(daily, key, unit))
    month_blk = period_block(month, key, unit) if month else None
    quarter_blk = period_block(quarter, key, unit) if quarter else None
    return f"""<tr>
      <td class="metric-cell">
        <div class="metric">
          <div class="icon">{metric['icon']}</div>
          <div class="metric-name">{metric['label']}</div>
        </div>
      </td>
      <td class="day-cell"><div class="num num-day">{day_val_s}</div></td>
      {render_period_cell(month_blk, unit)}
      {render_period_cell(quarter_blk, unit)}
    </tr>"""


def render_html(day_dict: dict) -> str:
    iso = day_dict["date"]
    asof = (date.fromisoformat(iso) + timedelta(days=1)).isoformat()
    tmpl = TEMPLATE.read_text(encoding="utf-8")
    rows = "\n".join(render_row(m, day_dict) for m in METRIC_ROWS)
    return (
        tmpl
        .replace("{{date_human}}", ru_date(iso))
        .replace("{{asof_human}}", ru_date(asof))
        .replace("{{month_label}}", month_label(day_dict.get("month") or {}, iso))
        .replace("{{quarter_label}}", quarter_label(day_dict.get("quarter") or {}))
        .replace("{{rows_html}}", rows)
    )


# ────────────────────────── playwright ──────────────────────────

async def screenshot(html: str, out_path: Path, width: int = 1024) -> None:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": width, "height": 800},
                                      device_scale_factor=2)
        await page.set_content(html, wait_until="networkidle")
        await page.locator(".card").screenshot(path=str(out_path), omit_background=False)
        await browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("date", help="YYYY-MM-DD")
    ap.add_argument("--datamart", default=str(ROOT / "data" / "datamart.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--html", help="Сохранить HTML рядом для отладки")
    args = ap.parse_args()

    dm = json.loads(Path(args.datamart).read_text(encoding="utf-8"))
    day = next((d for d in dm["days"] if d["date"] == args.date), None)
    if not day:
        print(f"ERROR: {args.date} не найден в {args.datamart}", file=sys.stderr)
        return 2

    out_path = Path(args.out or ROOT / "data" / "images" / f"{args.date}.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    html = render_html(day)
    if args.html:
        Path(args.html).write_text(html, encoding="utf-8")
        print(f"html → {args.html}")

    asyncio.run(screenshot(html, out_path))
    print(f"OK: {out_path}  ({out_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
