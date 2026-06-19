"""
Загрузка локального датамарта и выдача среза за конкретную дату.
"""
from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path

DATAMART = Path(__file__).resolve().parent.parent / "data" / "datamart.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(DATAMART.read_text(encoding="utf-8"))


def list_dates() -> list[date]:
    return [date.fromisoformat(d["date"]) for d in _load()["days"]]


def get_day(d: date) -> dict:
    iso = d.isoformat()
    for row in _load()["days"]:
        if row["date"] == iso:
            return row
    available = ", ".join(x.isoformat() for x in list_dates())
    raise KeyError(f"{iso} не найден в датамарте. Доступно: {available}")
