const MAINSTREAM_POOL = [
  "0050", "0056", "006208", "00878", "00919", "00929",
  "1101", "1216", "1301", "1303", "1326", "1402", "1590", "2002",
  "2303", "2308", "2317", "2327", "2330", "2344", "2345", "2353",
  "2356", "2376", "2377", "2382", "2395", "2408", "2412", "2454",
  "2474", "2603", "2609", "2615", "2618", "2880", "2881", "2882",
  "2883", "2884", "2885", "2886", "2887", "2890", "2891", "2892",
  "3008", "3034", "3035", "3045", "3231", "3264", "3443", "3661",
  "3711", "4938", "5347", "5871", "5880", "6505"
];

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const mode = url.searchParams.get("mode") || "momentum";
  const candidateMode = url.searchParams.get("candidate_mode") || "mainstream";
  const limit = clamp(Number(url.searchParams.get("limit") || 10), 5, 10);
  const sample = url.searchParams.get("sample") === "true";
  const symbols = (url.searchParams.get("symbols") || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const pool = symbols.length ? symbols : MAINSTREAM_POOL;
  const recommendations = [];
  const excluded = [];

  for (const stockId of pool.slice(0, 60)) {
    const snapshot = sample
      ? sampleSnapshot(stockId)
      : await supabaseSnapshot(context.env, stockId);
    if (!snapshot) {
      excluded.push({ stock_id: stockId, reason: "資料不足" });
      continue;
    }

    const filterReason = filterSnapshot(snapshot, mode);
    if (filterReason) {
      excluded.push({ stock_id: stockId, reason: filterReason });
      continue;
    }

    const scored = scoreSnapshot(snapshot);
    if (scored.score_10 >= 5) recommendations.push(scored);
  }

  recommendations.sort((a, b) => b.score_10 - a.score_10);
  return json({
    disclaimer: "所有結果僅作為觀察名單，不作為投資建議；不承諾收益，請搭配自行研究與風險控管。",
    source: sample ? "sample" : "supabase",
    mode,
    candidate_mode: candidateMode,
    recommendations: recommendations.slice(0, limit),
    excluded: excluded.slice(0, 20),
    warnings: [],
  });
}

async function supabaseSnapshot(env, stockId) {
  if (!env.SUPABASE_URL || !env.SUPABASE_SERVICE_ROLE_KEY) return null;
  const headers = {
    apikey: env.SUPABASE_SERVICE_ROLE_KEY,
    Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}`,
  };
  const [stockRes, pricesRes, instRes, financialRes, revenueRes] = await Promise.all([
    fetch(`${env.SUPABASE_URL}/rest/v1/stocks?stock_id=eq.${stockId}&select=*`, { headers }),
    fetch(`${env.SUPABASE_URL}/rest/v1/daily_prices?stock_id=eq.${stockId}&select=*&order=trade_date.desc&limit=260`, { headers }),
    fetch(`${env.SUPABASE_URL}/rest/v1/institutional_trades?stock_id=eq.${stockId}&select=*&order=trade_date.desc&limit=20`, { headers }),
    fetch(`${env.SUPABASE_URL}/rest/v1/financial_quarters?stock_id=eq.${stockId}&select=*&order=quarter.desc&limit=4`, { headers }),
    fetch(`${env.SUPABASE_URL}/rest/v1/monthly_revenues?stock_id=eq.${stockId}&select=*&order=revenue_month.desc&limit=1`, { headers }),
  ]);
  const stock = await stockRes.json();
  const prices = await pricesRes.json();
  const institutions = await instRes.json();
  const financials = await financialRes.json();
  const revenues = await revenueRes.json();
  if (!prices.length || !financials.length) return null;
  return buildSnapshotFromRows(stock[0] || { stock_id: stockId, stock_name: stockId }, prices.reverse(), institutions.reverse(), financials, revenues[0]);
}

function buildSnapshotFromRows(stock, prices, institutions, financials, revenue) {
  const close = prices.map((row) => Number(row.close));
  const high = prices.map((row) => Number(row.high));
  const low = prices.map((row) => Number(row.low));
  const volume = prices.map((row) => Number(row.volume));
  const last = prices.at(-1);
  const eps = financials.map((row) => Number(row.eps || 0)).reverse();
  return {
    stock_id: stock.stock_id,
    stock_name: stock.stock_name || stock.stock_id,
    price: Number(last.close),
    ma5: avg(close.slice(-5)),
    ma10: avg(close.slice(-10)),
    ma20: avg(close.slice(-20)),
    ma60: avg(close.slice(-60)),
    ma20_slope: avg(close.slice(-20)) - avg(close.slice(-25, -5)),
    volume: Number(last.volume),
    vol_ma5: avg(volume.slice(-5)),
    vol_ma60: avg(volume.slice(-60)),
    volume_ratio: Number(last.volume) / avg(volume.slice(-5)),
    high_20d: Math.max(...high.slice(-20)),
    high_52w: Math.max(...high.slice(-252)),
    return_20d_pct: ((close.at(-1) / close.at(-21)) - 1) * 100,
    rsi: rsi(close),
    atr: atr(high, low, close),
    bb_upper: avg(close.slice(-20)) + 2 * std(close.slice(-20)),
    revenue_yoy: revenue ? Number(revenue.revenue_yoy || 0) : null,
    roe: Number(financials[0]?.roe || 0),
    eps_last_4q: eps,
    pe: Number(financials[0]?.pe || 0),
    pe_3y_avg: avg(financials.map((row) => Number(row.pe || 0)).filter(Boolean)) || Number(financials[0]?.pe || 0),
    investment_trust_streak: buyStreak(institutions.map((row) => Number(row.investment_trust_net_buy || 0))),
    foreign_5d: institutions.slice(-5).reduce((sum, row) => sum + Number(row.foreign_net_buy || 0), 0),
    large_holder_change: 0,
    margin_balance_change_5d_pct: 0,
  };
}

function sampleSnapshot(stockId) {
  const seed = Array.from(stockId).reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const base = 45 + (seed % 160);
  const close = Array.from({ length: 260 }, (_, i) => base * (0.82 + i * 0.0014) + Math.sin(i / 7 + seed) * 2);
  const high = close.map((value, i) => value * (1.01 + (i % 4) * 0.002));
  const low = close.map((value, i) => value * (0.99 - (i % 3) * 0.002));
  const volume = close.map((_, i) => 1800 + ((i * seed) % 7000));
  volume[259] *= 1.7;
  const roe = [9, 12, 16, 21, 26, 18, 14, 30, 10][seed % 9];
  const revenueYoy = [15, 25, 55, 90, 35, 10, 68, 22, 48][seed % 9];
  return {
    stock_id: stockId,
    stock_name: stockId,
    price: close.at(-1),
    ma5: avg(close.slice(-5)),
    ma10: avg(close.slice(-10)),
    ma20: avg(close.slice(-20)),
    ma60: avg(close.slice(-60)),
    ma20_slope: avg(close.slice(-20)) - avg(close.slice(-25, -5)),
    volume: volume.at(-1),
    vol_ma5: avg(volume.slice(-5)),
    vol_ma60: avg(volume.slice(-60)),
    volume_ratio: volume.at(-1) / avg(volume.slice(-5)),
    high_20d: Math.max(...high.slice(-20)),
    high_52w: Math.max(...high),
    return_20d_pct: ((close.at(-1) / close.at(-21)) - 1) * 100,
    rsi: rsi(close),
    atr: atr(high, low, close),
    bb_upper: avg(close.slice(-20)) + 2 * std(close.slice(-20)),
    revenue_yoy: revenueYoy,
    roe,
    eps_last_4q: [1.2, 1.5, 1.8, 2.1],
    pe: [16, 18, 22, 28, 14, 20, 24, 30, 12][seed % 9],
    pe_3y_avg: [20, 20, 20, 24, 18, 20, 22, 28, 16][seed % 9],
    investment_trust_streak: 5 + (seed % 4),
    foreign_5d: 1000,
    large_holder_change: 0.8,
    margin_balance_change_5d_pct: 2,
  };
}

function filterSnapshot(s, mode) {
  if (sum(s.eps_last_4q || []) < 0) return "近四季 EPS 合計為負";
  if (s.roe < 8) return "最近一季 ROE < 8%";
  if (s.vol_ma60 < 800) return "近 3 個月平均成交量太低";
  if (s.price < 20) return "股價低於 20 元";
  if (s.return_20d_pct > 80) return "近 20 日漲幅超過 80%，標記過熱";
  if (!(s.price > s.ma20)) return "收盤價未站上 MA20";
  if (!(s.ma5 > s.ma20 || s.ma10 > s.ma20)) return "MA5/MA10 未站上 MA20";
  if (!(s.volume_ratio > 0.8)) return "成交量未達 5 日均量 x 0.8";
  if (!(s.price > s.high_52w * 0.7)) return "現價未達 52 週高點的 70%";
  if (mode === "accumulation" && !(Math.abs(s.price - s.ma20) / s.ma20 <= 0.08 || Math.abs(s.price - s.ma60) / s.ma60 <= 0.1)) return "蓄勢模式要求股價接近 MA20 或 MA60";
  if (mode === "momentum" && !(s.price > s.ma10 && s.ma5 > s.ma20 && s.volume_ratio > 1.5)) return "動能模式要求股價站上 MA10、MA5 > MA20、量比 > 1.5";
  return "";
}

function scoreSnapshot(s) {
  const fundamental = clamp(scoreFundamental(s), -12, 30);
  const technical = clamp(scoreTechnical(s), -8, 30);
  const chip = clamp(scoreChip(s), -10, 30);
  const market = clamp((s.return_20d_pct > 45 && s.volume_ratio > 2.5 ? 0 : 3) + 2 + 3, 0, 10);
  const score10 = Math.round(clamp(fundamental + technical + chip + market, 0, 100)) / 10;
  return {
    stock_id: s.stock_id,
    stock_name: s.stock_name,
    price: s.price,
    score_10: score10,
    fundamental_score: fundamental,
    technical_score: technical,
    chip_score: chip,
    market_score: market,
    grade: grade(score10),
    observation_zone: `不要直接用市價追；觀察 MA5 ${s.ma5.toFixed(2)}、MA10 ${s.ma10.toFixed(2)}、MA20 ${s.ma20.toFixed(2)}、前高回測 ${s.high_20d.toFixed(2)} 附近`,
    stop_loss: stopLoss(s),
    take_profit: `布林上軌 ${s.bb_upper.toFixed(2)}、前波高點 ${s.high_20d.toFixed(2)}、或沿 MA10/MA20 移動停利`,
    risks: risks(s),
    labels: s.rsi > 75 ? ["RSI 過熱追價風險"] : [],
    data_status: "OK",
  };
}

function scoreFundamental(s) {
  let score = 0;
  if (s.revenue_yoy > 80) score += 10;
  else if (s.revenue_yoy > 50) score += 8;
  else if (s.revenue_yoy > 20) score += 5;
  else if (s.revenue_yoy > 0) score += 2;
  else score -= 5;
  if (s.roe >= 25) score += 8;
  else if (s.roe >= 20) score += 6;
  else if (s.roe >= 15) score += 4;
  else if (s.roe >= 10) score += 2;
  const eps = s.eps_last_4q || [];
  if (avg(eps.slice(-2)) > avg(eps.slice(-4, -2))) score += 6;
  else score += 2;
  if (s.pe < s.pe_3y_avg) score += 6;
  else if (s.pe <= s.pe_3y_avg * 1.15) score += 3;
  else if (s.pe > s.pe_3y_avg * 1.35) score -= 3;
  return score;
}

function scoreTechnical(s) {
  let score = 0;
  if (s.price > s.ma20) score += 5;
  if (s.ma5 > s.ma20) score += 5;
  if (s.ma20_slope > 0) score += 5;
  if (s.volume_ratio > 2) score += 8;
  else if (s.volume_ratio >= 1.5) score += 5;
  if (s.rsi >= 45 && s.rsi <= 60) score += 6;
  else if (s.rsi > 60 && s.rsi <= 70) score += 3;
  else if (s.rsi > 75) score -= 5;
  if ((s.high_20d - s.price) / s.high_20d <= 0.1) score += 4;
  return score;
}

function scoreChip(s) {
  let score = 0;
  if (s.investment_trust_streak >= 5) score += 10;
  else if (s.investment_trust_streak >= 3) score += 7;
  else if (s.investment_trust_streak === 2) score += 4;
  else if (s.investment_trust_streak === 1) score += 2;
  if (s.foreign_5d > 0) score += 4;
  score += s.margin_balance_change_5d_pct > 10 ? -5 : 5;
  if (s.large_holder_change > 0) score += 6;
  return score;
}

function stopLoss(s) {
  const pct = clamp((2 * s.atr) / s.price, 0.015, 0.07);
  return `2 x ATR 參考，限制後約 ${(pct * 100).toFixed(1)}%，價位約 ${(s.price * (1 - pct)).toFixed(2)}`;
}

function risks(s) {
  const items = [];
  if (s.volume_ratio > 2.5 && s.return_20d_pct > 35) items.push("高檔爆量");
  if (s.margin_balance_change_5d_pct > 10) items.push("融資暴增");
  if (s.rsi > 75) items.push("RSI 過熱");
  return items.length ? items : ["資料面未顯示主要風險，但仍需人工確認"];
}

function grade(score) {
  if (score >= 8) return "強勢觀察";
  if (score >= 6.5) return "分批觀察";
  if (score >= 5) return "等待回測";
  return "排除";
}

function buyStreak(values) {
  let streak = 0;
  for (let i = values.length - 1; i >= 0; i -= 1) {
    if (values[i] > 0) streak += 1;
    else break;
  }
  return streak;
}

function rsi(values, period = 14) {
  const slice = values.slice(-(period + 1));
  let gains = 0;
  let losses = 0;
  for (let i = 1; i < slice.length; i += 1) {
    const diff = slice[i] - slice[i - 1];
    if (diff >= 0) gains += diff;
    else losses -= diff;
  }
  if (losses === 0) return 100;
  const rs = gains / losses;
  return 100 - 100 / (1 + rs);
}

function atr(high, low, close, period = 14) {
  const ranges = [];
  for (let i = Math.max(1, close.length - period); i < close.length; i += 1) {
    ranges.push(Math.max(high[i] - low[i], Math.abs(high[i] - close[i - 1]), Math.abs(low[i] - close[i - 1])));
  }
  return avg(ranges);
}

function avg(values) {
  const clean = values.filter((value) => Number.isFinite(value));
  return clean.length ? sum(clean) / clean.length : 0;
}

function sum(values) {
  return values.reduce((total, value) => total + Number(value || 0), 0);
}

function std(values) {
  const mean = avg(values);
  return Math.sqrt(avg(values.map((value) => (value - mean) ** 2)));
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

