// Lee la paleta activa desde las custom properties de :root, así los gráficos
// (Chart.js + heatmap dibujado en JS) siguen al tema claro/oscuro sin duplicar colores.
function getPalette() {
  const s = getComputedStyle(document.documentElement);
  const v = (name) => s.getPropertyValue(name).trim();
  return {
    ink: v("--ink"),
    secondary: v("--secondary"),
    muted: v("--muted"),
    grid: v("--grid"),
    blue: v("--primary"),
    orange: v("--cat-orange"),
    aqua: v("--cat-aqua"),
    violet: v("--cat-violet"),
    good: v("--good"),
    critical: v("--critical"),
    divBlue: v("--div-blue"),
    divGray: v("--div-gray"),
    divRed: v("--div-red"),
  };
}

const state = {
  selected: { ...(window.__DEFAULTS__ || {}) },
  charts: [],
  lastHistories: null,
  lastCorr: null,
};

const els = {
  tickerList: document.getElementById("ticker-list"),
  searchInput: document.getElementById("search-input"),
  searchResults: document.getElementById("search-results"),
  rangeSelect: document.getElementById("range-select"),
  intervalSelect: document.getElementById("interval-select"),
  generateBtn: document.getElementById("generate-btn"),
  statusMsg: document.getElementById("status-msg"),
  emptyState: document.getElementById("empty-state"),
  results: document.getElementById("results"),
  summaryCards: document.getElementById("summary-cards"),
  statsTable: document.getElementById("stats-table"),
  corrHeatmap: document.getElementById("corr-heatmap"),
  corrTable: document.getElementById("corr-table"),
  chartsGrid: document.getElementById("charts-grid"),
  themeToggle: document.getElementById("theme-toggle"),
};

// ---------- Tema claro/oscuro ----------

const THEME_KEY = "market-analysis-theme";

function storedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch (e) {
    return null;
  }
}

function effectiveTheme() {
  const explicit = document.documentElement.getAttribute("data-theme");
  if (explicit) return explicit;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme) {
  if (theme === "dark" || theme === "light") {
    document.documentElement.setAttribute("data-theme", theme);
  } else {
    document.documentElement.removeAttribute("data-theme");
  }
  if (els.themeToggle) {
    els.themeToggle.textContent = effectiveTheme() === "dark" ? "☀️" : "🌙";
  }
}

els.themeToggle?.addEventListener("click", () => {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  applyTheme(next);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch (e) {}
  if (state.lastHistories) renderCharts(state.lastHistories);
  renderCorrelation(state.lastCorr);
});

applyTheme(storedTheme());

function truncateLabel(name, maxLen = 15) {
  return name.length <= maxLen ? name : name.slice(0, maxLen - 1) + "…";
}

function fmtNum(value, decimals = 2) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString("es-ES", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

// ---------- Selección de instrumentos ----------

function renderTickerList() {
  els.tickerList.innerHTML = "";
  const names = Object.keys(state.selected);
  if (names.length === 0) {
    const li = document.createElement("li");
    li.className = "ticker-empty";
    li.textContent = "Ninguno seleccionado.";
    els.tickerList.appendChild(li);
    return;
  }
  names.forEach((name) => {
    const symbol = state.selected[name];
    const li = document.createElement("li");
    li.className = "ticker-item";

    const span = document.createElement("span");
    span.textContent = `${name} (${symbol})`;
    span.title = `${name} (${symbol})`;

    const btn = document.createElement("button");
    btn.className = "remove-btn";
    btn.textContent = "✕";
    btn.addEventListener("click", () => {
      delete state.selected[name];
      renderTickerList();
    });

    li.appendChild(span);
    li.appendChild(btn);
    els.tickerList.appendChild(li);
  });
}

// ---------- Buscador ----------

let searchDebounce = null;
els.searchInput.addEventListener("input", () => {
  const q = els.searchInput.value.trim();
  clearTimeout(searchDebounce);
  if (q.length < 2) {
    els.searchResults.hidden = true;
    els.searchResults.innerHTML = "";
    return;
  }
  searchDebounce = setTimeout(() => runSearch(q), 300);
});

async function runSearch(query) {
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const matches = await res.json();
    renderSearchResults(matches);
  } catch (err) {
    els.searchResults.hidden = true;
  }
}

function renderSearchResults(matches) {
  els.searchResults.innerHTML = "";
  if (!matches.length) {
    els.searchResults.hidden = true;
    return;
  }
  matches.forEach((m) => {
    const item = document.createElement("div");
    item.className = "search-result-item";

    const main = document.createElement("div");
    main.textContent = `${m.name} — ${m.symbol}`;
    const detail = document.createElement("small");
    detail.textContent = `${m.exchange || ""} · ${m.type || ""}`;
    item.appendChild(main);
    item.appendChild(detail);

    item.addEventListener("click", () => {
      state.selected[m.name] = m.symbol;
      renderTickerList();
      els.searchResults.hidden = true;
      els.searchInput.value = "";
    });
    els.searchResults.appendChild(item);
  });
  els.searchResults.hidden = false;
}

document.addEventListener("click", (e) => {
  if (!els.searchResults.contains(e.target) && e.target !== els.searchInput) {
    els.searchResults.hidden = true;
  }
});

// ---------- Tabs ----------

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------- Generar ----------

function setStatus(message, type) {
  if (!message) {
    els.statusMsg.hidden = true;
    return;
  }
  els.statusMsg.hidden = false;
  els.statusMsg.textContent = message;
  els.statusMsg.className = `status-msg ${type || ""}`;
}

els.generateBtn.addEventListener("click", async () => {
  const tickers = state.selected;
  if (Object.keys(tickers).length === 0) {
    setStatus("Selecciona al menos un instrumento.", "error");
    return;
  }
  setStatus("");
  els.generateBtn.disabled = true;
  els.generateBtn.textContent = "Descargando...";
  try {
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tickers,
        range: els.rangeSelect.value,
        interval: els.intervalSelect.value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(data.error || "Error desconocido.", "error");
      return;
    }
    renderResults(data);
  } catch (err) {
    setStatus("No se pudo conectar con el servidor.", "error");
  } finally {
    els.generateBtn.disabled = false;
    els.generateBtn.textContent = "🚀 Generar";
  }
});

function renderResults(data) {
  els.emptyState.hidden = true;
  els.results.hidden = false;
  state.lastHistories = data.histories;
  state.lastCorr = data.corr;
  renderSummary(data.summary);
  renderStats(data.stats);
  renderCorrelation(data.corr);
  renderCharts(data.histories);
}

// ---------- Resumen ----------

function renderSummary(rows) {
  els.summaryCards.innerHTML = "";
  rows.forEach((row) => {
    const variacion = row["Variación %"];
    const deltaClass = variacion == null ? "" : variacion >= 0 ? "up" : "down";
    const deltaSign = variacion == null ? "" : variacion >= 0 ? "▲" : "▼";

    const card = document.createElement("div");
    card.className = "metric-card";
    card.innerHTML = `
      <div class="label">${row.Nombre}</div>
      <div class="value">${row.Precio != null ? fmtNum(row.Precio) + " " + (row.Moneda || "") : "—"}</div>
      ${variacion != null ? `<div class="delta ${deltaClass}">${deltaSign} ${fmtNum(Math.abs(variacion))} %</div>` : ""}
      ${row["Máx 52 sem"] != null ? `<div class="range">52 sem: ${fmtNum(row["Mín 52 sem"])} – ${fmtNum(row["Máx 52 sem"])}</div>` : ""}
    `;
    els.summaryCards.appendChild(card);
  });
}

// ---------- Estadísticas ----------

function renderStats(rows) {
  const cols = ["Nombre", "Retorno anualizado %", "Volatilidad anualizada %", "Sharpe", "Máx drawdown %"];
  let html = "<thead><tr>" + cols.map((c) => `<th>${c}</th>`).join("") + "</tr></thead><tbody>";
  rows.forEach((row) => {
    html += "<tr>" + cols.map((c) => `<td>${c === "Nombre" ? row[c] : fmtNum(row[c])}</td>`).join("") + "</tr>";
  });
  html += "</tbody>";
  els.statsTable.innerHTML = html;
}

// ---------- Correlación ----------

function hexToRgb(hex) {
  const v = hex.replace("#", "");
  return [parseInt(v.substr(0, 2), 16), parseInt(v.substr(2, 2), 16), parseInt(v.substr(4, 2), 16)];
}
function rgbToHex([r, g, b]) {
  return "#" + [r, g, b].map((x) => Math.round(x).toString(16).padStart(2, "0")).join("");
}
function lerp(a, b, t) { return a + (b - a) * t; }
function lerpColor(c1, c2, t) { return [lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t)]; }

function makeDivergingScale(palette) {
  const divBlue = hexToRgb(palette.divBlue);
  const divGray = hexToRgb(palette.divGray);
  const divRed = hexToRgb(palette.divRed);
  return (value) => {
    if (value <= 0) return rgbToHex(lerpColor(divBlue, divGray, value + 1));
    return rgbToHex(lerpColor(divGray, divRed, value));
  };
}

function renderCorrelation(corr) {
  els.corrHeatmap.innerHTML = "";
  els.corrTable.innerHTML = "";

  if (!corr) {
    const p = document.createElement("p");
    p.className = "corr-empty";
    p.textContent = "Selecciona al menos dos instrumentos para ver la correlación.";
    els.corrHeatmap.appendChild(p);
    return;
  }

  const palette = getPalette();
  const divergingColor = makeDivergingScale(palette);
  const { labels, matrix } = corr;
  els.corrHeatmap.style.gridTemplateColumns = `repeat(${labels.length + 1}, auto)`;

  els.corrHeatmap.appendChild(document.createElement("div"));
  labels.forEach((l) => {
    const cell = document.createElement("div");
    cell.className = "heatmap-label";
    cell.textContent = truncateLabel(l, 10);
    els.corrHeatmap.appendChild(cell);
  });

  labels.forEach((rowLabel, i) => {
    const rowLabelCell = document.createElement("div");
    rowLabelCell.className = "heatmap-label";
    rowLabelCell.textContent = truncateLabel(rowLabel, 10);
    els.corrHeatmap.appendChild(rowLabelCell);

    labels.forEach((_, j) => {
      const value = matrix[i][j];
      const cell = document.createElement("div");
      cell.className = "heatmap-cell";
      if (value == null) {
        cell.style.background = palette.divGray;
        cell.style.color = palette.muted;
        cell.textContent = "—";
      } else {
        cell.style.background = divergingColor(value);
        cell.style.color = Math.abs(value) > 0.55 ? "#fff" : palette.ink;
        cell.textContent = value.toFixed(2);
      }
      els.corrHeatmap.appendChild(cell);
    });
  });

  let html = "<thead><tr><th></th>" + labels.map((l) => `<th>${l}</th>`).join("") + "</tr></thead><tbody>";
  labels.forEach((rowLabel, i) => {
    html += `<tr><th>${rowLabel}</th>` + matrix[i].map((v) => `<td>${v == null ? "—" : v.toFixed(2)}</td>`).join("") + "</tr>";
  });
  html += "</tbody>";
  els.corrTable.innerHTML = html;
}

// ---------- Gráficos ----------

function chartOptions(palette, { legend = true, yMin, yMax } = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: {
        display: legend,
        position: "top",
        labels: { boxWidth: 10, usePointStyle: true, color: palette.secondary, font: { size: 10 } },
      },
      tooltip: { mode: "index", intersect: false },
    },
    scales: {
      x: { ticks: { color: palette.muted, maxTicksLimit: 6, font: { size: 9 } }, grid: { color: palette.grid } },
      y: { min: yMin, max: yMax, ticks: { color: palette.muted, font: { size: 9 } }, grid: { color: palette.grid } },
    },
  };
}

function renderCharts(histories) {
  state.charts.forEach((c) => c.destroy());
  state.charts = [];
  els.chartsGrid.innerHTML = "";

  const palette = getPalette();

  Object.entries(histories).forEach(([name, rows]) => {
    const card = document.createElement("div");
    card.className = "chart-card";
    card.innerHTML = `
      <h3>${truncateLabel(name)}</h3>
      <div class="price-canvas-wrap"><canvas class="price-canvas"></canvas></div>
      <div class="rsi-canvas-wrap"><canvas class="rsi-canvas"></canvas></div>
    `;
    els.chartsGrid.appendChild(card);

    const labels = rows.map((r) => r.Date.slice(0, 10));

    const priceChart = new Chart(card.querySelector(".price-canvas").getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "Close", data: rows.map((r) => r.Close), borderColor: palette.ink, borderWidth: 1.4, pointRadius: 0, tension: 0.05 },
          { label: "SMA20", data: rows.map((r) => r.SMA20), borderColor: palette.blue, borderDash: [5, 3], borderWidth: 1.2, pointRadius: 0, tension: 0.05 },
          { label: "SMA50", data: rows.map((r) => r.SMA50), borderColor: palette.orange, borderDash: [5, 3], borderWidth: 1.2, pointRadius: 0, tension: 0.05 },
          { label: "EMA20", data: rows.map((r) => r.EMA20), borderColor: palette.aqua, borderDash: [2, 2], borderWidth: 1.2, pointRadius: 0, tension: 0.05 },
        ],
      },
      options: chartOptions(palette, { legend: true }),
    });
    state.charts.push(priceChart);

    const rsiChart = new Chart(card.querySelector(".rsi-canvas").getContext("2d"), {
      type: "line",
      data: {
        labels,
        datasets: [
          { label: "RSI14", data: rows.map((r) => r.RSI14), borderColor: palette.violet, borderWidth: 1.2, pointRadius: 0, tension: 0.05 },
          { label: "Sobrecompra (70)", data: rows.map(() => 70), borderColor: palette.critical, borderWidth: 0.8, borderDash: [4, 4], pointRadius: 0 },
          { label: "Sobreventa (30)", data: rows.map(() => 30), borderColor: palette.good, borderWidth: 0.8, borderDash: [4, 4], pointRadius: 0 },
        ],
      },
      options: chartOptions(palette, { legend: false, yMin: 0, yMax: 100 }),
    });
    state.charts.push(rsiChart);
  });
}

// ---------- Mayores subidas del día ----------

async function loadTopGainers() {
  const container = document.getElementById("top-gainers-list");
  if (!container) return;
  try {
    const res = await fetch("/api/top-gainers?count=10");
    const rows = await res.json();
    renderTopGainers(rows);
  } catch (err) {
    container.innerHTML = '<p class="gainers-status">No se pudieron cargar las subidas del día.</p>';
  }
}

function renderTopGainers(rows) {
  const container = document.getElementById("top-gainers-list");
  container.innerHTML = "";
  if (!rows || !rows.length) {
    container.innerHTML = '<p class="gainers-status">Sin datos disponibles ahora mismo.</p>';
    return;
  }
  rows.forEach((row) => {
    const card = document.createElement("div");
    card.className = "gainer-card";
    card.innerHTML = `
      <div class="gainer-info">
        <span class="gainer-symbol">${row.symbol}</span>
        <span class="gainer-name" title="${row.name}">${row.name}</span>
      </div>
      <span class="gainer-change">▲ ${row.change_percent != null ? row.change_percent.toFixed(2) : "—"}%</span>
      <button class="gainer-add-btn" type="button" title="Añadir a seleccionados">+</button>
    `;
    card.querySelector(".gainer-add-btn").addEventListener("click", () => {
      state.selected[row.name] = row.symbol;
      renderTickerList();
    });
    container.appendChild(card);
  });
}

renderTickerList();
loadTopGainers();
