const runBtn = document.querySelector("#runBtn");
const brokerBtn = document.querySelector("#brokerBtn");
const statusBox = document.querySelector("#status");
const resultsBox = document.querySelector("#results");
const brokerResult = document.querySelector("#brokerResult");

runBtn.addEventListener("click", async () => {
  statusBox.textContent = "篩選中...";
  resultsBox.innerHTML = "";
  const params = new URLSearchParams({
    mode: document.querySelector("#mode").value,
    candidate_mode: document.querySelector("#candidateMode").value,
    limit: document.querySelector("#limit").value,
    sample: document.querySelector("#sample").checked ? "true" : "false",
  });
  const symbols = document.querySelector("#symbols").value.trim();
  if (symbols) params.set("symbols", symbols);

  try {
    const response = await fetch(`/api/recommend?${params.toString()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    renderResults(data);
  } catch (error) {
    statusBox.textContent = `執行失敗：${error.message}`;
  }
});

brokerBtn.addEventListener("click", async () => {
  const stock = document.querySelector("#brokerStock").value.trim();
  const broker = document.querySelector("#brokerName").value.trim();
  if (!stock || !broker) {
    brokerResult.textContent = "請輸入股票代號與分點名稱。";
    return;
  }
  brokerResult.textContent = "分析中...";
  const params = new URLSearchParams({ stock, broker });
  try {
    const response = await fetch(`/api/analyze-broker?${params.toString()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    brokerResult.textContent = JSON.stringify(data, null, 2);
  } catch (error) {
    brokerResult.textContent = `執行失敗：${error.message}`;
  }
});

function renderResults(data) {
  const list = data.recommendations || [];
  statusBox.textContent = list.length
    ? `本次產生 ${list.length} 檔觀察標的`
    : "本次沒有符合條件的主名單。";

  if (!list.length) {
    const excluded = data.excluded || [];
    resultsBox.innerHTML = `<article class="stock-card"><strong>排除原因</strong><div class="detail-list">${excluded
      .slice(0, 10)
      .map((item) => `<div>${escapeHtml(item.stock_id)}：${escapeHtml(item.reason)}</div>`)
      .join("")}</div></article>`;
    return;
  }

  resultsBox.innerHTML = list.map(renderCard).join("");
}

function renderCard(item) {
  return `
    <article class="stock-card">
      <div class="stock-head">
        <div>
          <div class="stock-title">${escapeHtml(item.stock_name)} ${escapeHtml(item.stock_id)}</div>
          <div class="grade">${escapeHtml(item.grade)} · 現價 ${formatPrice(item.price)}</div>
        </div>
        <div class="score">${Number(item.score_10).toFixed(1)}<div class="grade">/10</div></div>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>基本面</span><strong>${Number(item.fundamental_score).toFixed(1)}/30</strong></div>
        <div class="metric"><span>技術面</span><strong>${Number(item.technical_score).toFixed(1)}/30</strong></div>
        <div class="metric"><span>籌碼面</span><strong>${Number(item.chip_score).toFixed(1)}/30</strong></div>
        <div class="metric"><span>市場行為</span><strong>${Number(item.market_score).toFixed(1)}/10</strong></div>
      </div>
      <div class="detail-list">
        <div><strong>進場觀察區：</strong>${escapeHtml(item.observation_zone)}</div>
        <div><strong>停損參考：</strong>${escapeHtml(item.stop_loss)}</div>
        <div><strong>停利參考：</strong>${escapeHtml(item.take_profit)}</div>
        <div class="risk"><strong>主要風險：</strong>${escapeHtml((item.risks || []).join("、"))}</div>
      </div>
    </article>
  `;
}

function formatPrice(value) {
  return value === null || value === undefined ? "資料不足" : Number(value).toFixed(2);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

