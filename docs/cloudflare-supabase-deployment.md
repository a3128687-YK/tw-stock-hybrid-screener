# Cloudflare Pages + Supabase SQL 部署說明

這條路線不需要在使用者電腦安裝 Python。網站由 Cloudflare Pages 提供，資料庫由 Supabase Postgres 提供，API 由 Cloudflare Pages Functions 執行。

## 架構

```text
瀏覽器
  -> Cloudflare Pages 靜態網頁
  -> Cloudflare Pages Functions /api/recommend
  -> Supabase REST API / Postgres SQL
```

## 1. 建立 Supabase 資料庫

1. 進入 Supabase 專案。
2. 打開 SQL Editor。
3. 貼上並執行：

```text
supabase/schema.sql
```

4. 可選：貼上並執行示範股票清單：

```text
supabase/seed.sql
```

目前資料表包含：

- `stocks`
- `daily_prices`
- `institutional_trades`
- `monthly_revenues`
- `financial_quarters`
- `margin_trades`
- `large_holder_stats`
- `broker_branch_trades`
- `screening_runs`
- `screening_results`

分點資料表已保留，但不主動抓取付費或登入資料。

## 2. 建立 Cloudflare Pages 專案

Cloudflare Pages 設定：

```text
Root directory: cloudflare-pages
Build command: 空白
Build output directory: public
```

如果 Cloudflare 要求 build command，可以填：

```bash
echo "static site"
```

## 3. Cloudflare 環境變數

到 Cloudflare Pages 專案：

```text
Settings -> Environment variables
```

新增：

```text
SUPABASE_URL=https://你的專案.supabase.co
SUPABASE_SERVICE_ROLE_KEY=你的 service_role key
```

注意：`SUPABASE_SERVICE_ROLE_KEY` 只放在 Cloudflare Pages Functions 環境變數，不要寫進前端 JS 或公開檔案。

正式接 FinMind 匯入資料時，可再新增：

```text
FINMIND_TOKEN=你的 FinMind token
```

目前 Cloudflare Pages 版本已能：

- 用示範資料跑觀察名單。
- 從 Supabase 表格讀正式資料。
- 查詢分點行為表。

## 4. 部署後使用

打開 Cloudflare Pages 網址後：

1. 勾選「示範資料」可立即測試畫面與評分流程。
2. 取消「示範資料」會改讀 Supabase 正式資料。
3. 如果 Supabase 尚未匯入股價、財報、法人資料，系統會顯示「資料不足」。

## 5. 下一步：資料匯入

Cloudflare Pages 適合跑網站與輕量 API，不適合長時間批次抓全市場資料。建議後續二選一：

- 用 Supabase Edge Function 定時抓 FinMind，寫入 Supabase。
- 用 GitHub Actions 每天收盤後抓 FinMind，寫入 Supabase。

這兩種都可以保留合法公開資料來源，也方便未來接 LINE 通知。

