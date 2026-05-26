insert into public.stocks (stock_id, stock_name, market, industry, is_etf) values
  ('0050', '元大台灣50', 'TWSE', 'ETF', true),
  ('0056', '元大高股息', 'TWSE', 'ETF', true),
  ('2330', '台積電', 'TWSE', '半導體', false),
  ('2454', '聯發科', 'TWSE', '半導體', false),
  ('3035', '智原', 'TWSE', '半導體', false),
  ('3228', '金麗科', 'TPEX', '半導體', false),
  ('3443', '創意', 'TWSE', '半導體', false),
  ('3661', '世芯-KY', 'TWSE', '半導體', false)
on conflict (stock_id) do update set
  stock_name = excluded.stock_name,
  market = excluded.market,
  industry = excluded.industry,
  is_etf = excluded.is_etf,
  updated_at = now();

