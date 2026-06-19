"""
Smoke-тест: парсер → форматтер должны воспроизвести оригинальное сообщение
байт-в-байт по каждому дню в датамарте.

    python -m pytest tests/  (если установлен pytest)
    python tests/test_round_trip.py  (standalone)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot import datamart
from bot.formatter import format_summary

RAW = ROOT / "data" / "raw_messages.txt"


def split_original(text: str) -> dict[str, str]:
    pat = re.compile(r"Ежедневная сводка ППМ\s*—\s*(\d{2}\.\d{2}\.\d{4})")
    matches = list(pat.finditer(text))
    out = {}
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end].rstrip()
        d = m.group(1)
        y, mo, dd = d.split(".")[2], d.split(".")[1], d.split(".")[0]
        out[f"{y}-{mo}-{dd}"] = block
    return out


def normalize(s: str) -> str:
    """Trim trailing, схлопнуть множественные пустые строки до одной."""
    lines = [ln.rstrip() for ln in s.splitlines()]
    out = []
    prev_blank = False
    for ln in lines:
        blank = not ln
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    while out and not out[-1]:
        out.pop()
    return "\n".join(out)


def main() -> int:
    originals = split_original(RAW.read_text(encoding="utf-8"))
    fails = 0
    for d in datamart.list_dates():
        iso = d.isoformat()
        generated = normalize(format_summary(datamart.get_day(d)))
        expected = normalize(originals[iso])
        if generated == expected:
            print(f"OK  {iso}")
        else:
            fails += 1
            print(f"FAIL {iso}")
            # diff первой расходящейся строки
            for g, e in zip(generated.splitlines(), expected.splitlines()):
                if g != e:
                    print(f"  expected: {e!r}")
                    print(f"  got     : {g!r}")
                    break
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
