export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const stock = url.searchParams.get("stock");
  const broker = url.searchParams.get("broker");
  if (!stock || !broker) {
    return json({ error: "請輸入 stock 與 broker" }, 400);
  }
  if (!context.env.SUPABASE_URL || !context.env.SUPABASE_SERVICE_ROLE_KEY) {
    return json({
      stock_id: stock,
      broker,
      data_status: "資料不足",
      message: "尚未設定 Supabase 環境變數，或尚未匯入合法可用的券商分點資料。",
    });
  }

  const endpoint = `${context.env.SUPABASE_URL}/rest/v1/broker_branch_trades?stock_id=eq.${encodeURIComponent(stock)}&broker_name=eq.${encodeURIComponent(broker)}&select=*&order=trade_date.asc`;
  const response = await fetch(endpoint, {
    headers: {
      apikey: context.env.SUPABASE_SERVICE_ROLE_KEY,
      Authorization: `Bearer ${context.env.SUPABASE_SERVICE_ROLE_KEY}`,
    },
  });
  const rows = await response.json();
  if (!rows.length) {
    return json({
      stock_id: stock,
      broker,
      data_status: "資料不足",
      message: "尚未匯入合法可用的券商分點資料，因此 broker_behavior 模式暫不啟用評分。",
    });
  }

  const result = {
    stock_id: stock,
    broker,
    data_status: "OK",
    samples: rows.length,
    next_day_sell_rate: rate(rows, "next_day_reverse_sell", (value) => value === true),
    next_day_win_rate: rate(rows, "next_day_return", (value) => Number(value) > 0),
    win_rate_3d: rate(rows, "return_3d", (value) => Number(value) > 0),
    win_rate_5d: rate(rows, "return_5d", (value) => Number(value) > 0),
    avg_return_5d: avg(rows.map((row) => Number(row.return_5d)).filter(Number.isFinite)),
    avg_max_drawdown: avg(rows.map((row) => Number(row.max_drawdown)).filter(Number.isFinite)),
  };
  result.suspected_day_trade_broker = result.next_day_sell_rate >= 0.6 && result.avg_return_5d < 0.5;
  result.suspected_swing_broker = result.win_rate_5d >= 0.55 && result.next_day_sell_rate < 0.4;
  return json(result);
}

function rate(rows, key, predicate) {
  const values = rows.map((row) => row[key]).filter((value) => value !== null && value !== undefined);
  if (!values.length) return 0;
  return Math.round((values.filter(predicate).length / values.length) * 1000) / 1000;
}

function avg(values) {
  if (!values.length) return 0;
  return Math.round((values.reduce((sum, value) => sum + value, 0) / values.length) * 1000) / 1000;
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}

