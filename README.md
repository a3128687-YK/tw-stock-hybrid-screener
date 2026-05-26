# 台股混合型選股輔助系統

這是一套用來產生台股「觀察名單」的 Python 專案骨架。它不宣稱買進推薦、不承諾收益，也不會抓取付費會員內容或繞過登入。

資料來源優先採用公開、可合法取得的資料：目前主要接 FinMind API，並保留 TWSE OpenAPI fallback 與本地 SQLite 資料表。FinMind 官方文件列出可取用台股價格、月營收、財報、法人買賣超等資料集；TWSE OpenAPI 也提供公開交易資料端點。參考來源：[FinMind API docs](https://api.finmindtrade.com/docs)、[FinMind 文件](https://finmind.github.io/v3/)、[TWSE OpenAPI swagger](https://openapi.twse.com.tw/v1/swagger.json)。

## 專案架構

```text
tw-stock-hybrid-screener/
  main.py
  pyproject.toml
  requirements.txt
  .env.example
  docs/
    schema.sql
  tests/
    test_scoring.py
  tw_stock_screener/
    config.py
    models.py
    database.py
    indicators.py
    candidate_pools.py
    filters.py
    scoring.py
    screener.py
    broker_behavior.py
    reporting.py
    data_sources/
      finmind.py
      twse.py
      repository.py
      sample.py
```

## 安裝

```bash
cd "C:\Users\88692\Documents\New project\tw-stock-hybrid-screener"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

可選：設定 FinMind token。

```bash
set FINMIND_TOKEN=你的_token
```

## CLI 指令

初始化資料庫：

```bash
python main.py init-db
```

使用主流股池跑動能模式：

```bash
python main.py recommend
```

使用蓄勢模式：

```bash
python main.py recommend --mode accumulation
```

使用自訂觀察池：

```bash
python main.py recommend --candidate-mode custom --symbols 3228,3661,3443,3035
```

用內建假資料檢查輸出格式：

```bash
python main.py recommend --sample --mode momentum --symbols 3228,3661,3443,3035
```

分點行為分析：

```bash
python main.py analyze-broker --stock 3228 --broker 凱基台北
```

分點資料目前不主動抓取，必須先把合法來源資料匯入 `broker_branch_trades`。若沒有資料，系統會顯示「資料不足」。

## 網站版

本專案也已經包含網站介面，入口是 `web_app.py`，畫面檔案在 `web/static/`。

本機啟動：

```bash
uvicorn web_app:app --reload --host 127.0.0.1 --port 8000
```

打開：

```text
http://127.0.0.1:8000
```

網站功能：

- 選擇 `momentum` 或 `accumulation`。
- 選擇主流股池、投信連買池或自訂觀察池。
- 輸入股票代號，例如 `3228,3661,3443,3035`。
- 產生 5~10 檔觀察名單。
- 查看每檔的分數、觀察區、停損參考、停利參考與主要風險。
- 分點行為分析入口已保留；未匯入合法分點資料時會顯示資料不足。

### 部署到網站

最簡單可用 Render：

1. 把這個資料夾上傳到 GitHub repository。
2. 到 Render 建立 `New Web Service`。
3. 選擇該 repository。
4. Build command：

```bash
pip install -r requirements.txt
```

5. Start command：

```bash
uvicorn web_app:app --host 0.0.0.0 --port $PORT
```

6. 在環境變數設定 `FINMIND_TOKEN`。

專案也已附上 `render.yaml` 與 `Procfile`，支援 Render 或類似 Python Web 平台。

## Cloudflare Pages + Supabase SQL 版本

如果不想架 Python 伺服器，也可以用和先前專案相近的方式部署：

- Cloudflare Pages：放網站畫面。
- Cloudflare Pages Functions：提供 `/api/recommend` 與 `/api/analyze-broker`。
- Supabase SQL：存股票、股價、法人、營收、財報、融資、大戶與分點資料。

新增檔案：

```text
cloudflare-pages/
  public/
  functions/api/recommend.js
  functions/api/analyze-broker.js
supabase/
  schema.sql
  seed.sql
docs/cloudflare-supabase-deployment.md
```

部署步驟請看：

```text
docs/cloudflare-supabase-deployment.md
```

## 候選池

- `institution_accumulation`：以近 12 個交易日投信連買天數排序，取前 60 檔。初版用主流池當 seed，未來可改為全市場清單。
- `mainstream`：設定檔寫死 60 檔流動性較佳的主流股與熱門 ETF，作為備援。
- `custom`：使用者輸入股票代號清單。

## 評分與排除

硬性排除包含 EPS、ROE、成交量、低價股、短線過熱與爆量長上影風險。第一階段技術面要求站上 MA20、短均線轉強、量能達標、現價未遠離 52 週高點太多，並標記 RSI 過熱。

總分 100 分，再轉換成 10 分制：

- 基本面 30 分：月營收 YoY、ROE、EPS 趨勢、PE 位置。
- 技術面 30 分：MA20、MA5/MA20、MA20 斜率、量比、RSI、距離 20 日高點。
- 籌碼面 30 分：投信連買、外資 5 日買超、融資變化、大戶持股、預留分點分數。
- 市場行為 10 分：題材、未過度擁擠、大盤環境。

分級：

- 8.0 以上：強勢觀察
- 6.5~7.9：分批觀察
- 5.0~6.4：等待回測
- 5.0 以下：排除

## 範例輸出

```text
所有結果僅作為觀察名單，不作為投資建議；不承諾收益，請搭配自行研究與風險控管。

台股混合型選股觀察名單
排名 股票       現價   綜合/10 基本 技術 籌碼 市場 分級
1    3228 3228  118.50 7.8     24/30 23/30 24/30 7/10 分批觀察

3228 3228
進場觀察區：不要直接用市價追；觀察 MA5 116.20、MA10 112.80、MA20 106.40、前高回測 121.00 附近
停損參考：2 x ATR 參考，限制後約 4.8%，價位約 112.81
停利參考：布林上軌 123.50、前波高點 121.00、或沿 MA10/MA20 移動停利
主要風險：高檔爆量、RSI 過熱
```

## 後續擴充點

- LINE 通知：在 `reporting.py` 後接通知 adapter。
- 網頁儀表板：讓 `screener.py` 回傳 JSON 給 FastAPI 或 Streamlit。
- 分點資料庫：匯入合法來源後，`broker_behavior.py` 可直接計算隔日賣出率、3/5 日勝率、平均報酬與最大回撤。
- 權重調整：目前在 `config.py` 的 `ScoreWeights`，之後可改成 YAML 或資料庫設定。
