# Ruka-na-Pulse Bot

Telegram-бот «рука на пульсе»: каждое утро в 07:20 МСК шлёт CFO компактную сводку
вчерашнего дня (DAU, новые карты по тарифам, GMV, Revenue, Gross Profit, Net Profit)
+ накопительный план/факт за месяц и квартал с run-rate.

Это **портфолио-версия** бота: вместо боевого Reports API + ClickHouse читает
локальный JSON-датамарт `data/datamart.json` с архивом исторических сводок.
Формат выходного сообщения и поведение sender-а полностью идентичны production-варианту.

## Пример сообщения

```
Ежедневная сводка ППМ — 03.06.2026

• Новых клиентов: 1 293
• Новых карт: 1 402
   – Travel: 538
   – Premium: 48
   – Subscriptions: 816

• GMV: 61 291 114 ₽
   – за выпуск карт: 5 006 057 ₽
   – за пополнения: 56 285 057 ₽

• Revenue: 11 108 845 ₽
• Gross Profit: 9 499 780 ₽
• Чистая прибыль: 4 809 985 ₽

───────────────

📊 За Июнь 2026

• GMV: 173 150 752 ₽ из 1 650 000 000 ₽ (10,5%) · RR 104,9%
• Gross Profit: 23 310 734 ₽ из 230 000 000 ₽ (10,1%) · RR 101,4%
• Чистая прибыль: 9 976 345 ₽ из 90 000 000 ₽ (11,1%) · RR 110,8%

───────────────

📊 За Q2 2026

• GMV: 2 718 799 455 ₽ из 4 000 000 000 ₽ (68,0%) · RR 96,6%
• Чистая прибыль: 181 475 216 ₽ из 200 000 000 ₽ (90,7%) · RR 129,0%
```

(полный текст — `docs/sample_2026-06-03.txt`)

## Архитектура

```
┌────────────────┐    07:20 МСК
│  launchd plist │ ─────────┐
└────────────────┘          │
                            ▼
              ┌────────────────────────────┐
              │  ppm-daily-bot.sh (runner) │
              │  • cd <repo>               │
              │  • venv python -m bot.sender
              │  • log rotation            │
              └────────────────────────────┘
                            │
                            ▼
              ┌────────────────────────────┐
              │  bot.sender                │ ◀── CLI: YYYY-MM-DD / --dry-run
              └────────────────────────────┘
                  │              │
                  ▼              ▼
       ┌──────────────┐  ┌─────────────────┐
       │ bot.datamart │  │ bot.formatter   │
       │ читает день  │  │ собирает текст  │
       │ из JSON      │  │ по контракту    │
       └──────────────┘  └─────────────────┘
                            │
                            ▼
                  Telegram Bot API → CFO DM
```

### Прод vs. портфолио

| Слой              | Прод                                       | Портфолио (этот репо)               |
|-------------------|--------------------------------------------|-------------------------------------|
| Источник метрик   | KokoBank Reports API + ClickHouse          | `data/datamart.json` (8 дней)       |
| Расписание        | launchd 07:20 МСК (macOS)                  | то же plist в комплекте             |
| Сеть              | Tailscale exit-node KZ (обход РКН для TG)  | любая сеть с доступом к api.telegram.org |
| Форматтер         | `bot/formatter.py`                         | без изменений                       |
| Sender            | `bot/sender.py`                            | без изменений                       |

## Датамарт

API больше недоступен (токен `ppm_live_*` отозван при ротации доступов).
Чтобы кейс был запускаемым, исторические сводки за `27.05.2026 — 03.06.2026`
сохранены в Telegram-архив и распарсены в JSON:

```bash
python tools/parse_messages.py
# data/raw_messages.txt → data/datamart.json
```

Парсер регулярными выражениями вытягивает все 30+ полей из каждого сообщения
(daily / month / quarter, plan vs actual, run-rate, OpEx/ComEx с количеством
прошедших дней). Round-trip проверка гарантирует, что регенерированное из
датамарта сообщение совпадает с оригиналом байт-в-байт:

```bash
python tests/test_round_trip.py
# OK  2026-05-27 ... OK  2026-06-03
```

## Запуск

```bash
python -m venv .venv && source .venv/bin/activate     # macOS/Linux
# .venv\Scripts\activate                              # Windows

# Smoke-test без Telegram:
python -m bot.sender 2026-06-03 --dry-run

# Реальная отправка в Telegram:
cp .env.example .env  # заполнить BOT_TOKEN, CHAT_IDS
python -m bot.sender 2026-06-03
```

## Schedule (production)

На целевой машине:

```bash
mkdir -p ~/bin ~/Library/LaunchAgents ~/Logs/ppm-daily-bot
cp deploy/ppm-daily-bot.sh ~/bin/ && chmod +x ~/bin/ppm-daily-bot.sh
cp deploy/com.vitalygoreshnev.ppm-daily-bot.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.vitalygoreshnev.ppm-daily-bot.plist
```

## Файлы

```
bot/
  sender.py         CLI + Telegram отправка
  datamart.py       загрузка JSON-датамарта по дате
  formatter.py      сборка текста сводки
data/
  raw_messages.txt  архив исторических TG-сводок
  datamart.json     структурированный датамарт (sha-локированный source of truth)
tools/
  parse_messages.py raw_messages.txt → datamart.json
tests/
  test_round_trip.py datamart → formatter → совпадение с оригиналом
deploy/
  ppm-daily-bot.sh                   обёртка для launchd
  com.vitalygoreshnev.ppm-daily-bot.plist  расписание 07:20 МСК
docs/
  sample_*.txt      примеры выводов для презентации
```

## Лицензия

MIT (см. LICENSE).
