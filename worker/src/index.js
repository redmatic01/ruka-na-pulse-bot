// Telegram-webhook handler для Cloudflare Workers.
//
// Команды:
//   /start  — приветствие + клавиатура с датами
//   /demo   — последняя сводка (03.06.2026)
//   /dates  — клавиатура с датами
//   YYYY-MM-DD callback — сводка за дату
//
// BOT_TOKEN — secret в Wrangler.

import datamart from "./datamart.json";
import { formatSummary } from "./formatter.js";

const BOT_NAME = "Ruka-na-Pulse Demo";

function findDay(iso) {
  return datamart.days.find((d) => d.date === iso) || null;
}

function datesKeyboard() {
  const rows = [];
  let row = [];
  for (const d of datamart.days) {
    const [, m, day] = d.date.split("-");
    row.push({ text: `${day}.${m}`, callback_data: d.date });
    if (row.length === 4) {
      rows.push(row);
      row = [];
    }
  }
  if (row.length) rows.push(row);
  return { inline_keyboard: rows };
}

async function tg(token, method, body) {
  const r = await fetch(`https://api.telegram.org/bot${token}/${method}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return r.json();
}

async function handleUpdate(update, env) {
  const token = env.BOT_TOKEN;

  // Inline-кнопка с датой.
  if (update.callback_query) {
    const q = update.callback_query;
    const chatId = q.message.chat.id;
    const iso = q.data;
    const day = findDay(iso);
    if (day) {
      await tg(token, "sendMessage", {
        chat_id: chatId,
        text: formatSummary(day),
        disable_web_page_preview: true,
      });
    } else {
      await tg(token, "sendMessage", { chat_id: chatId, text: `Нет данных за ${iso}` });
    }
    await tg(token, "answerCallbackQuery", { callback_query_id: q.id });
    return;
  }

  const msg = update.message;
  if (!msg || !msg.text) return;
  const chatId = msg.chat.id;
  const text = msg.text.trim();

  if (text.startsWith("/start")) {
    const welcome =
      `👋 Это демо-бот «${BOT_NAME}» для портфолио.\n\n` +
      `В проде он каждое утро в 07:20 МСК отправляет CFO компактную сводку ` +
      `вчерашнего дня (DAU, новые карты по тарифам, GMV, Revenue, Gross Profit, ` +
      `Net Profit) + накопительный план/факт за месяц и квартал.\n\n` +
      `Нажми на любую дату ниже, чтобы получить реальную сводку из исторического архива ` +
      `27.05.2026 – 03.06.2026.\n\n` +
      `Команды: /demo — последняя сводка, /dates — выбрать дату.\n` +
      `Код: github.com/redmatic01/ruka-na-pulse-bot`;
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text: welcome,
      reply_markup: datesKeyboard(),
      disable_web_page_preview: true,
    });
    return;
  }

  if (text.startsWith("/demo")) {
    const latest = datamart.days[datamart.days.length - 1];
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text: formatSummary(latest),
      disable_web_page_preview: true,
    });
    return;
  }

  if (text.startsWith("/dates")) {
    await tg(token, "sendMessage", {
      chat_id: chatId,
      text: "Выбери дату:",
      reply_markup: datesKeyboard(),
    });
    return;
  }

  // YYYY-MM-DD в чате — тоже принимаем.
  const iso = text.match(/^(\d{4}-\d{2}-\d{2})$/)?.[1];
  if (iso) {
    const day = findDay(iso);
    if (day) {
      await tg(token, "sendMessage", {
        chat_id: chatId,
        text: formatSummary(day),
        disable_web_page_preview: true,
      });
    } else {
      await tg(token, "sendMessage", {
        chat_id: chatId,
        text: `Нет данных за ${iso}. Попробуй /dates`,
      });
    }
    return;
  }

  await tg(token, "sendMessage", {
    chat_id: chatId,
    text: "Не понимаю. /start /demo /dates или YYYY-MM-DD",
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/" || url.pathname === "/health") {
      return new Response(
        `OK — ${BOT_NAME} webhook is up. ${datamart.days.length} days in datamart (${datamart.period.from} → ${datamart.period.to}).`,
        { headers: { "Content-Type": "text/plain; charset=utf-8" } }
      );
    }

    if (url.pathname === "/telegram" && request.method === "POST") {
      const update = await request.json();
      // fire-and-forget — отвечаем Телеграму сразу 200.
      await handleUpdate(update, env).catch((e) => console.error(e));
      return new Response("ok");
    }

    return new Response("not found", { status: 404 });
  },
};
