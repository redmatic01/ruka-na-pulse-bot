// JS-форматтер сводки. Зеркалит bot/formatter.py байт-в-байт.

const NBSP = " "; // обычный пробел (исторический формат бота)
const SEP = "───────────────";

export function fmtInt(n) {
  const x = Math.trunc(n);
  const abs = Math.abs(x);
  const s = String(abs).replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return x < 0 ? "−" + s : s;
}

export function fmtPct(x) {
  return (x * 100).toFixed(1).replace(".", ",") + "%";
}

function planTail(p, withRub = false) {
  if (!p || p.plan == null) return "";
  const rub = withRub ? `${NBSP}₽` : "";
  return ` из ${fmtInt(p.plan)}${rub} (${fmtPct(p.pct_of_plan)}) · RR ${fmtPct(p.run_rate)}`;
}

function formatDaily(day, header) {
  const out = [header, ""];
  const dly = day.daily;
  out.push(`• Новых клиентов: ${fmtInt(dly.new_clients)}`);
  out.push(`• Новых карт: ${fmtInt(dly.new_cards.total)}`);
  out.push(`   – Travel: ${fmtInt(dly.new_cards.travel)}`);
  out.push(`   – Premium: ${fmtInt(dly.new_cards.premium)}`);
  out.push(`   – Subscriptions: ${fmtInt(dly.new_cards.subscriptions)}`);
  out.push("");
  out.push(`• GMV: ${fmtInt(dly.gmv.total)}${NBSP}₽`);
  out.push(`   – за выпуск карт: ${fmtInt(dly.gmv.cards_issue)}${NBSP}₽`);
  out.push(`   – за пополнения: ${fmtInt(dly.gmv.topups)}${NBSP}₽`);
  out.push("");
  out.push(`• Revenue: ${fmtInt(dly.revenue.total)}${NBSP}₽`);
  out.push(`   – с открытия карт: ${fmtInt(dly.revenue.cards_issue)}${NBSP}₽`);
  out.push(`   – с пополнений: ${fmtInt(dly.revenue.topups)}${NBSP}₽`);
  out.push("");
  const gp = dly.gross_profit;
  out.push(`• Gross Profit: ${fmtInt(gp.total)}${NBSP}₽`);
  if (gp.cards_issue != null) out.push(`   – GP с открытия карт: ${fmtInt(gp.cards_issue)}${NBSP}₽`);
  if (gp.topups != null) out.push(`   – GP с пополнений: ${fmtInt(gp.topups)}${NBSP}₽`);
  out.push(`   – OpEx: ${fmtInt(gp.opex)}${NBSP}₽`);
  out.push(`   – ComEx: ${fmtInt(gp.comex)}${NBSP}₽`);
  out.push("");
  out.push(`• Чистая прибыль: ${fmtInt(dly.net_profit)}${NBSP}₽`);
  return out;
}

function formatPeriod(p) {
  const out = ["", SEP, "", `📊 За ${p.label}`, ""];
  const nc = p.new_clients;
  out.push(`• Новых клиентов: ${fmtInt(nc.actual)}${planTail(nc)}`);
  const cards = p.new_cards;
  out.push(`• Новых карт: ${fmtInt(cards.actual)}${planTail(cards)}`);
  out.push(`   – Travel: ${fmtInt(cards.travel)}`);
  out.push(`   – Premium: ${fmtInt(cards.premium)}`);
  out.push(`   – Subscriptions: ${fmtInt(cards.subscriptions)}`);
  out.push("");
  const gmv = p.gmv;
  out.push(`• GMV: ${fmtInt(gmv.actual)}${NBSP}₽${planTail(gmv, true)}`);
  out.push(`   – за выпуск карт: ${fmtInt(gmv.cards_issue)}${NBSP}₽`);
  out.push(`   – за пополнения: ${fmtInt(gmv.topups)}${NBSP}₽`);
  out.push("");
  const rev = p.revenue;
  out.push(`• Revenue: ${fmtInt(rev.actual)}${NBSP}₽`);
  out.push(`   – с открытия карт: ${fmtInt(rev.cards_issue)}${NBSP}₽`);
  out.push(`   – с пополнений: ${fmtInt(rev.topups)}${NBSP}₽`);
  out.push("");
  const gp = p.gross_profit;
  out.push(`• Gross Profit: ${fmtInt(gp.actual)}${NBSP}₽${planTail(gp, true)}`);
  if (gp.cards_issue != null) out.push(`   – GP с открытия карт: ${fmtInt(gp.cards_issue)}${NBSP}₽`);
  if (gp.topups != null) out.push(`   – GP с пополнений: ${fmtInt(gp.topups)}${NBSP}₽`);
  const daysTail = p.days_elapsed ? ` (за ${p.days_elapsed}${NBSP}дн.)` : "";
  out.push(`   – OpEx: ${fmtInt(gp.opex)}${NBSP}₽${daysTail}`);
  out.push(`   – ComEx: ${fmtInt(gp.comex)}${NBSP}₽${daysTail}`);
  out.push("");
  const np = p.net_profit;
  out.push(`• Чистая прибыль: ${fmtInt(np.actual)}${NBSP}₽${planTail(np, true)}`);
  return out;
}

export function formatSummary(day) {
  const [y, m, d] = day.date.split("-");
  const header = `Ежедневная сводка ППМ — ${d}.${m}.${y}`;
  let lines = formatDaily(day, header);
  if (day.month) lines = lines.concat(formatPeriod(day.month));
  if (day.quarter) lines = lines.concat(formatPeriod(day.quarter));
  return lines.join("\n");
}
