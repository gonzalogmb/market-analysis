// Chart.js usa su propia fuente por defecto (Helvetica/Arial) si no se le indica otra cosa;
// la igualamos a la del resto de la web para que los gráficos no desentonen.
if (window.Chart) {
  Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
}

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

const canUseCartera = !window.__LOGIN_ENABLED__ || !!window.__AUTHENTICATED__;

const state = {
  selected: { ...(window.__DEFAULTS__ || {}) },
  charts: [],
  lastHistories: null,
  lastCorr: null,
  lastStats: null,
  lastGainers: null,
  lastPortfolio: null,
  transactions: [],
  portfolioChart: null,
  lang: "es",
  fundCollapsed: {},
};

const COLLAPSE_THRESHOLD = 5;

const els = {
  tickerList: document.getElementById("ticker-list"),
  searchInput: document.getElementById("search-input"),
  searchResults: document.getElementById("search-results"),
  rangeSelect: document.getElementById("range-select"),
  intervalSelect: document.getElementById("interval-select"),
  generateBtn: document.getElementById("generate-btn"),
  statusMsg: document.getElementById("status-msg"),
  marketHints: document.querySelectorAll(".market-empty-hint"),
  summaryCards: document.getElementById("summary-cards"),
  statsTable: document.getElementById("stats-table"),
  statsWrap: document.querySelector("#tab-stats .table-wrap"),
  corrHeatmap: document.getElementById("corr-heatmap"),
  corrTable: document.getElementById("corr-table"),
  corrLayout: document.querySelector("#tab-corr .corr-layout"),
  chartsGrid: document.getElementById("charts-grid"),
  themeToggle: document.getElementById("theme-toggle"),
  langEnBtn: document.getElementById("lang-en"),
  langEsBtn: document.getElementById("lang-es"),
  portfolioLoginHint: document.getElementById("portfolio-login-hint"),
  portfolioContent: document.getElementById("portfolio-content"),
  subtabButtons: document.querySelectorAll(".subtab-btn"),
  portfolioManageList: document.getElementById("portfolio-manage-list"),
  portfolioManageStatus: document.getElementById("portfolio-manage-status"),
  portfolioEmpty: document.getElementById("portfolio-empty"),
  portfolioWarning: document.getElementById("portfolio-warning"),
  portfolioSummary: document.getElementById("portfolio-summary"),
  portfolioTable: document.getElementById("portfolio-table"),
  portfolioTableWrap: document.querySelector(".portfolio-table-wrap"),
  portfolioChartCard: document.querySelector(".portfolio-chart-card"),
  portfolioCanvas: document.getElementById("portfolio-canvas"),
};

// Los botones con icono llevan el texto en un <span class="btn-label">; cambiar
// btn.textContent directamente borraría también el <svg> del icono.
function setBtnLabel(btn, text) {
  const label = btn.querySelector(".btn-label");
  if (label) label.textContent = text;
  else btn.textContent = text;
}

// ---------- Idioma ----------

const LANG_KEY = "market-analysis-lang";

const translations = {
  es: {
    pageTitle: "Market Analysis",
    subtitle: "Yahoo Finance · indicadores · correlaciones",
    selectedInstruments: "Instrumentos seleccionados",
    noneSelected: "Ninguno seleccionado.",
    searchInstrument: "Buscar instrumento",
    searchPlaceholder: "ej. Apple, oro, S&P 500...",
    historicalRange: "Rango histórico",
    interval: "Intervalo",
    generate: "Generar",
    generating: "Descargando...",
    topGainersTitle: "Mayores subidas del día",
    loading: "Cargando...",
    gainersError: "No se pudieron cargar las subidas del día.",
    gainersEmpty: "Sin datos disponibles ahora mismo.",
    addToSelected: "Añadir a seleccionados",
    emptyStateHtml: "Elige instrumentos en la barra lateral y pulsa <strong>Generar</strong>.",
    tabResumen: "Resumen",
    tabStats: "Estadísticas",
    tabCorr: "Correlación",
    tabCharts: "Gráficos",
    selectAtLeastOne: "Selecciona al menos un instrumento.",
    unknownError: "Error desconocido.",
    connectionError: "No se pudo conectar con el servidor.",
    correlationEmpty: "Selecciona al menos dos instrumentos para ver la correlación.",
    weekRangeLabel: "52 sem",
    themeToggleTitle: "Cambiar tema",
    overboughtLabel: "Sobrecompra (70)",
    oversoldLabel: "Sobreventa (30)",
    locale: "es-ES",
    statCols: {
      Nombre: "Nombre",
      "Retorno anualizado %": "Retorno anualizado %",
      "Volatilidad anualizada %": "Volatilidad anualizada %",
      Sharpe: "Sharpe",
      "Máx drawdown %": "Máx drawdown %",
    },
    myPortfolio: "Mi cartera",
    subtabStatus: "Estado actual",
    subtabManage: "Gestionar cartera",
    portfolioIntro: "Registra aportaciones o retiradas por instrumento — el estado se recalcula solo.",
    portfolioNoneSelected: "Elige instrumentos en la barra lateral para poder añadirlos a tu cartera.",
    tabPortfolio: "Mi cartera",
    portfolioEmpty: "Añade un movimiento en «Gestionar cartera» para ver aquí el estado de tu cartera.",
    portfolioChartTitle: "Cartera vs S&P 500",
    totalInvested: "Invertido",
    currentValue: "Valor actual",
    totalGain: "Ganancia",
    vsBenchmark: "vs S&P 500",
    portfolioSeriesLabel: "Tu cartera",
    benchmarkSeriesLabel: "S&P 500 (mismo importe/fechas)",
    currencyWarning: "No se pudo convertir a EUR el tipo de cambio de: ",
    logout: "Cerrar sesión",
    loginBtn: "Iniciar sesión",
    portfolioLoginHint: "Inicia sesión (botón arriba a la izquierda) para usar tu cartera personal.",
    fundNetLabel: "Participaciones netas",
    noMovements: "Sin movimientos todavía.",
    movementsLabel: "movimientos",
    txDeposit: "Aportación",
    txWithdraw: "Retirada",
    txAddDeposit: "+ Aportar",
    txAddWithdraw: "− Retirar",
    txUnitsPlaceholder: "Participaciones",
    txAddBtn: "Añadir",
    txUnitsRequired: "Indica un número de participaciones distinto de 0.",
    txDateRequired: "Indica una fecha.",
    txLoadError: "No se pudieron cargar tus movimientos.",
    removeTitle: "Eliminar",
    portfolioCols: {
      name: "Nombre",
      invested: "Invertido neto",
      n_transactions: "Movimientos",
      current_price: "Precio actual",
      current_value: "Valor actual",
      gain_pct: "Ganancia %",
      weight_pct: "Peso %",
    },
  },
  en: {
    pageTitle: "Market Analysis",
    subtitle: "Yahoo Finance · indicators · correlations",
    selectedInstruments: "Selected instruments",
    noneSelected: "None selected.",
    searchInstrument: "Search instrument",
    searchPlaceholder: "e.g. Apple, gold, S&P 500...",
    historicalRange: "Historical range",
    interval: "Interval",
    generate: "Generate",
    generating: "Loading...",
    topGainersTitle: "Today's top gainers",
    loading: "Loading...",
    gainersError: "Could not load today's top gainers.",
    gainersEmpty: "No data available right now.",
    addToSelected: "Add to selected",
    emptyStateHtml: "Choose instruments in the sidebar and click <strong>Generate</strong>.",
    tabResumen: "Summary",
    tabStats: "Statistics",
    tabCorr: "Correlation",
    tabCharts: "Charts",
    selectAtLeastOne: "Select at least one instrument.",
    unknownError: "Unknown error.",
    connectionError: "Could not connect to the server.",
    correlationEmpty: "Select at least two instruments to see the correlation.",
    weekRangeLabel: "52 wk",
    themeToggleTitle: "Toggle theme",
    overboughtLabel: "Overbought (70)",
    oversoldLabel: "Oversold (30)",
    locale: "en-US",
    statCols: {
      Nombre: "Name",
      "Retorno anualizado %": "Annualized return %",
      "Volatilidad anualizada %": "Annualized volatility %",
      Sharpe: "Sharpe",
      "Máx drawdown %": "Max drawdown %",
    },
    myPortfolio: "My portfolio",
    subtabStatus: "Current status",
    subtabManage: "Manage portfolio",
    portfolioIntro: "Record deposits or withdrawals per instrument — the status recalculates automatically.",
    portfolioNoneSelected: "Choose instruments in the sidebar to add them to your portfolio.",
    tabPortfolio: "My portfolio",
    portfolioEmpty: "Add a movement in “Manage portfolio” to see your portfolio status here.",
    portfolioChartTitle: "Portfolio vs S&P 500",
    totalInvested: "Invested",
    currentValue: "Current value",
    totalGain: "Gain",
    vsBenchmark: "vs S&P 500",
    portfolioSeriesLabel: "Your portfolio",
    benchmarkSeriesLabel: "S&P 500 (same amount/dates)",
    currencyWarning: "Could not convert to EUR the exchange rate for: ",
    portfolioCols: {
      name: "Name",
      invested: "Net invested",
      n_transactions: "Movements",
      current_price: "Current price",
      current_value: "Current value",
      gain_pct: "Gain %",
      weight_pct: "Weight %",
    },
    logout: "Log out",
    loginBtn: "Log in",
    portfolioLoginHint: "Log in (top-left button) to use your personal portfolio.",
    fundNetLabel: "Net units",
    noMovements: "No movements yet.",
    movementsLabel: "movements",
    txDeposit: "Deposit",
    txWithdraw: "Withdrawal",
    txAddDeposit: "+ Deposit",
    txAddWithdraw: "− Withdraw",
    txUnitsPlaceholder: "Units",
    txAddBtn: "Add",
    txUnitsRequired: "Enter a non-zero number of units.",
    txDateRequired: "Enter a date.",
    txLoadError: "Could not load your movements.",
    removeTitle: "Remove",
  },
};

function storedLang() {
  try {
    return localStorage.getItem(LANG_KEY);
  } catch (e) {
    return null;
  }
}

function t(key) {
  return translations[state.lang][key];
}

function applyLanguage(lang) {
  state.lang = lang === "en" ? "en" : "es";
  document.documentElement.setAttribute("lang", state.lang);
  document.title = t("pageTitle");

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-html]").forEach((el) => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });

  els.langEnBtn?.classList.toggle("active", state.lang === "en");
  els.langEsBtn?.classList.toggle("active", state.lang === "es");

  if (!els.generateBtn.disabled) {
    setBtnLabel(els.generateBtn, t("generate"));
  }

  updatePortfolioAccess();

  renderTickerList();
  if (state.lastStats) renderStats(state.lastStats);
  renderCorrelation(state.lastCorr);
  if (state.lastGainers) renderTopGainers(state.lastGainers);
  if (state.lastPortfolio) renderPortfolio(state.lastPortfolio);

  try {
    localStorage.setItem(LANG_KEY, state.lang);
  } catch (e) {}
}

els.langEnBtn?.addEventListener("click", () => applyLanguage("en"));
els.langEsBtn?.addEventListener("click", () => applyLanguage("es"));

applyLanguage(storedLang() || "es");

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
    const icon = effectiveTheme() === "dark" ? "i-sun" : "i-moon";
    els.themeToggle.innerHTML = `<svg class="icon"><use href="#${icon}"/></svg>`;
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
  if (state.lastPortfolio) renderPortfolio(state.lastPortfolio);
});

applyTheme(storedTheme());

function truncateLabel(name, maxLen = 15) {
  return name.length <= maxLen ? name : name.slice(0, maxLen - 1) + "…";
}

function fmtNum(value, decimals = 2) {
  if (value === null || value === undefined) return "—";
  return Number(value).toLocaleString(t("locale"), {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtUnits(value) {
  return fmtNum(value, 4);
}

// ---------- Selección de instrumentos ----------

function renderTickerList() {
  els.tickerList.innerHTML = "";
  const names = Object.keys(state.selected);
  if (names.length === 0) {
    const li = document.createElement("li");
    li.className = "ticker-empty";
    li.textContent = t("noneSelected");
    els.tickerList.appendChild(li);
  } else {
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
  renderManageList();
}

// ---------- Mi cartera ----------
// La cartera se guarda en el servidor como un histórico de movimientos (aportaciones/retiradas)
// por instrumento, no como una única compra. El estado actual se recalcula automáticamente cada
// vez que se añade o borra un movimiento, sin necesidad de un botón "Calcular".

document.querySelectorAll(".subtab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".subtab-btn").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".subtab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`subtab-${btn.dataset.subtab}`).classList.add("active");
  });
});

function updatePortfolioAccess() {
  if (canUseCartera) {
    els.portfolioLoginHint.hidden = true;
    els.portfolioContent.hidden = false;
  } else {
    els.portfolioLoginHint.innerHTML = `<svg class="icon"><use href="#i-lock"/></svg><span>${t("portfolioLoginHint")}</span>`;
    els.portfolioLoginHint.hidden = false;
    els.portfolioContent.hidden = true;
  }
}

function setManageStatus(message, type) {
  if (!message) {
    els.portfolioManageStatus.hidden = true;
    return;
  }
  els.portfolioManageStatus.hidden = false;
  els.portfolioManageStatus.textContent = message;
  els.portfolioManageStatus.className = `status-msg ${type || ""}`;
}

function groupTransactionsByName() {
  const groups = {};
  state.transactions.forEach((tx) => {
    if (!groups[tx.name]) groups[tx.name] = { name: tx.name, symbol: tx.symbol, transactions: [] };
    groups[tx.name].transactions.push(tx);
  });
  return groups;
}

async function loadTransactionsFromServer() {
  try {
    const res = await fetch("/api/portfolio/transactions");
    if (!res.ok) return;
    const txs = await res.json();
    if (!Array.isArray(txs)) return;
    state.transactions = txs;
    txs.forEach((tx) => {
      if (!(tx.name in state.selected)) state.selected[tx.name] = tx.symbol;
    });
    renderTickerList();
    if (txs.length) recomputePortfolio();
  } catch (err) {
    setManageStatus(t("txLoadError"), "error");
  }
}

function renderManageList() {
  els.portfolioManageList.innerHTML = "";
  const names = Object.keys(state.selected);

  if (names.length === 0) {
    const p = document.createElement("p");
    p.className = "portfolio-empty-hint";
    p.textContent = t("portfolioNoneSelected");
    els.portfolioManageList.appendChild(p);
    return;
  }

  const grouped = groupTransactionsByName();

  names.forEach((name) => {
    const symbol = state.selected[name];
    const txs = (grouped[name] ? grouped[name].transactions : []).slice().sort((a, b) => a.date.localeCompare(b.date));
    const net = txs.reduce((sum, tx) => sum + tx.units, 0);

    if (!(name in state.fundCollapsed) && txs.length) {
      state.fundCollapsed[name] = txs.length > COLLAPSE_THRESHOLD;
    }
    const collapsed = state.fundCollapsed[name];

    const card = document.createElement("div");
    card.className = "fund-manager";

    const header = document.createElement("div");
    header.className = "fund-manager-header";
    header.innerHTML = `<span class="fund-name" title="${name}">${name}</span><span class="fund-net">${t("fundNetLabel")}: ${fmtUnits(net)}</span>`;
    if (txs.length > 0) {
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "fund-toggle";
      toggle.setAttribute("aria-expanded", String(!collapsed));
      toggle.innerHTML = `<span class="fund-toggle-chevron">${collapsed ? "▸" : "▾"}</span> ${txs.length} ${t("movementsLabel")}`;
      toggle.addEventListener("click", () => {
        state.fundCollapsed[name] = !state.fundCollapsed[name];
        renderManageList();
      });
      header.appendChild(toggle);
    }
    card.appendChild(header);

    if (txs.length) {
      const list = document.createElement("ul");
      list.className = "tx-list";
      list.hidden = collapsed;
      txs.forEach((tx) => {
        const isDeposit = tx.units >= 0;
        const li = document.createElement("li");
        li.className = "tx-item";
        li.innerHTML = `
          <span class="tx-date">${tx.date}</span>
          <span class="tx-badge ${isDeposit ? "deposit" : "withdraw"}">${isDeposit ? t("txDeposit") : t("txWithdraw")}</span>
          <span class="tx-amount">${isDeposit ? "+" : "−"} ${fmtUnits(Math.abs(tx.units))}</span>
          <button class="tx-delete" type="button" aria-label="${t("removeTitle")}">✕</button>
        `;
        li.querySelector(".tx-delete").addEventListener("click", () => deleteTransactionUI(tx.id));
        list.appendChild(li);
      });
      card.appendChild(list);
    } else {
      const p = document.createElement("p");
      p.className = "portfolio-empty-hint";
      p.textContent = t("noMovements");
      card.appendChild(p);
    }

    const addRow = document.createElement("div");
    addRow.className = "tx-add-row";
    addRow.innerHTML = `
      <div class="tx-type-toggle">
        <button type="button" class="tx-type-btn active" data-type="deposit">${t("txAddDeposit")}</button>
        <button type="button" class="tx-type-btn" data-type="withdraw">${t("txAddWithdraw")}</button>
      </div>
      <input type="number" class="tx-amount-input" min="0.0001" step="0.0001" placeholder="${t("txUnitsPlaceholder")}" />
      <input type="date" class="tx-date-input" />
      <button type="button" class="btn-outline tx-add-btn">${t("txAddBtn")}</button>
    `;
    let txType = "deposit";
    const typeButtons = addRow.querySelectorAll(".tx-type-btn");
    typeButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        typeButtons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        txType = btn.dataset.type;
      });
    });
    const unitsInput = addRow.querySelector(".tx-amount-input");
    const dateInput = addRow.querySelector(".tx-date-input");
    addRow.querySelector(".tx-add-btn").addEventListener("click", () => {
      const units = parseFloat(unitsInput.value);
      if (!(units > 0)) {
        setManageStatus(t("txUnitsRequired"), "error");
        return;
      }
      if (!dateInput.value) {
        setManageStatus(t("txDateRequired"), "error");
        return;
      }
      const signedUnits = txType === "withdraw" ? -units : units;
      addTransactionUI(name, symbol, signedUnits, dateInput.value, () => {
        unitsInput.value = "";
        dateInput.value = "";
      });
    });
    card.appendChild(addRow);

    els.portfolioManageList.appendChild(card);
  });
}

async function addTransactionUI(name, symbol, units, date, onSuccess) {
  setManageStatus("");
  try {
    const res = await fetch("/api/portfolio/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, symbol, units, date }),
    });
    const data = await res.json();
    if (!res.ok) {
      setManageStatus(data.error || t("unknownError"), "error");
      return;
    }
    state.transactions.push(data);
    renderManageList();
    recomputePortfolio();
    if (onSuccess) onSuccess();
  } catch (err) {
    setManageStatus(t("connectionError"), "error");
  }
}

async function deleteTransactionUI(id) {
  setManageStatus("");
  try {
    const res = await fetch(`/api/portfolio/transactions/${id}`, { method: "DELETE" });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setManageStatus(data.error || t("unknownError"), "error");
      return;
    }
    state.transactions = state.transactions.filter((tx) => tx.id !== id);
    renderManageList();
    recomputePortfolio();
  } catch (err) {
    setManageStatus(t("connectionError"), "error");
  }
}

async function recomputePortfolio() {
  const grouped = groupTransactionsByName();
  const holdings = Object.values(grouped)
    .map((h) => ({
      name: h.name,
      symbol: h.symbol,
      transactions: h.transactions.map((tx) => ({ units: tx.units, date: tx.date })),
    }))
    .filter((h) => h.transactions.length);

  if (!holdings.length) {
    state.lastPortfolio = null;
    els.portfolioEmpty.hidden = false;
    els.portfolioTableWrap.hidden = true;
    els.portfolioChartCard.hidden = true;
    els.portfolioSummary.innerHTML = "";
    return;
  }

  try {
    const res = await fetch("/api/portfolio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings }),
    });
    const data = await res.json();
    if (!res.ok) {
      setManageStatus(data.error || t("unknownError"), "error");
      return;
    }
    state.lastPortfolio = data;
    renderPortfolio(data);
  } catch (err) {
    setManageStatus(t("connectionError"), "error");
  }
}

function renderPortfolio(data) {
  els.portfolioEmpty.hidden = true;
  els.portfolioTableWrap.hidden = false;
  els.portfolioChartCard.hidden = false;
  els.portfolioSummary.innerHTML = "";
  els.portfolioTable.innerHTML = "";

  if (data.currency_warnings && data.currency_warnings.length) {
    els.portfolioWarning.hidden = false;
    els.portfolioWarning.className = "status-msg error";
    els.portfolioWarning.textContent = t("currencyWarning") + data.currency_warnings.join(", ");
  } else {
    els.portfolioWarning.hidden = true;
  }

  const palette = getPalette();
  const { benchmark } = data;

  // Los totales se recalculan sumando los valores de fila ya redondeados a 2 decimales
  // (los mismos que se ven en la tabla), en vez de usar el total sin redondear que manda
  // el servidor — así la tarjeta siempre "cuadra" con lo que se ve al sumar las filas.
  const round2 = (n) => Math.round(n * 100) / 100;
  const investedSum = round2(data.holdings.reduce((sum, h) => sum + round2(h.invested), 0));
  const currentValueSum = round2(data.holdings.reduce((sum, h) => sum + round2(h.current_value), 0));
  const gainPct = investedSum ? (currentValueSum / investedSum - 1) * 100 : null;

  const cards = [
    { label: t("totalInvested"), value: fmtNum(investedSum) + " €" },
    {
      label: t("currentValue"),
      value: fmtNum(currentValueSum) + " €",
      delta: gainPct,
      deltaText: gainPct != null ? `${gainPct >= 0 ? "▲" : "▼"} ${fmtNum(Math.abs(gainPct))} %` : null,
    },
  ];
  if (benchmark && gainPct != null && benchmark.gain_pct != null) {
    const diff = gainPct - benchmark.gain_pct;
    cards.push({
      label: t("vsBenchmark"),
      value: `${fmtNum(benchmark.gain_pct)} %`,
      delta: diff,
      deltaText: `${diff >= 0 ? "▲" : "▼"} ${fmtNum(Math.abs(diff))} pp`,
    });
  }

  cards.forEach((c) => {
    const card = document.createElement("div");
    card.className = "metric-card";
    const deltaClass = c.delta == null ? "" : c.delta >= 0 ? "up" : "down";
    card.innerHTML = `
      <div class="label">${c.label}</div>
      <div class="value">${c.value}</div>
      ${c.deltaText ? `<div class="delta ${deltaClass}">${c.deltaText}</div>` : ""}
    `;
    els.portfolioSummary.appendChild(card);
  });

  const cols = ["name", "invested", "n_transactions", "current_price", "current_value", "gain_pct", "weight_pct"];
  const colLabels = t("portfolioCols");
  let html = "<thead><tr>" + cols.map((c) => `<th>${colLabels[c] || c}</th>`).join("") + "</tr></thead><tbody>";
  data.holdings.forEach((row) => {
    html += "<tr>" + cols.map((c) => {
      if (c === "name" || c === "n_transactions") return `<td>${row[c]}</td>`;
      return `<td>${fmtNum(row[c])}</td>`;
    }).join("") + "</tr>";
  });
  html += "</tbody>";
  els.portfolioTable.innerHTML = html;

  if (state.portfolioChart) {
    state.portfolioChart.destroy();
    state.portfolioChart = null;
  }
  const labels = data.series.map((r) => r.date);
  const datasets = [
    { label: t("portfolioSeriesLabel"), data: data.series.map((r) => r.portfolio), borderColor: palette.blue, borderWidth: 1.6, pointRadius: 0, tension: 0.05 },
  ];
  if (data.series.some((r) => r.benchmark != null)) {
    datasets.push({
      label: t("benchmarkSeriesLabel"),
      data: data.series.map((r) => r.benchmark),
      borderColor: palette.orange,
      borderDash: [5, 3],
      borderWidth: 1.4,
      pointRadius: 0,
      tension: 0.05,
    });
  }
  state.portfolioChart = new Chart(els.portfolioCanvas.getContext("2d"), {
    type: "line",
    data: { labels, datasets },
    options: chartOptions(palette, { legend: true }),
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
    setStatus(t("selectAtLeastOne"), "error");
    return;
  }
  setStatus("");
  els.generateBtn.disabled = true;
  setBtnLabel(els.generateBtn, t("generating"));
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
      setStatus(data.error || t("unknownError"), "error");
      return;
    }
    renderResults(data);
  } catch (err) {
    setStatus(t("connectionError"), "error");
  } finally {
    els.generateBtn.disabled = false;
    setBtnLabel(els.generateBtn, t("generate"));
  }
});

function renderResults(data) {
  els.marketHints.forEach((el) => (el.hidden = true));
  els.statsWrap.hidden = false;
  els.corrLayout.hidden = false;
  state.lastHistories = data.histories;
  state.lastCorr = data.corr;
  state.lastStats = data.stats;
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
      ${row["Máx 52 sem"] != null ? `<div class="range">${t("weekRangeLabel")}: ${fmtNum(row["Mín 52 sem"])} – ${fmtNum(row["Máx 52 sem"])}</div>` : ""}
    `;
    els.summaryCards.appendChild(card);
  });
}

// ---------- Estadísticas ----------

function renderStats(rows) {
  state.lastStats = rows;
  const cols = ["Nombre", "Retorno anualizado %", "Volatilidad anualizada %", "Sharpe", "Máx drawdown %"];
  const statCols = t("statCols");
  let html = "<thead><tr>" + cols.map((c) => `<th>${statCols[c] || c}</th>`).join("") + "</tr></thead><tbody>";
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
    p.textContent = t("correlationEmpty");
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
          { label: t("overboughtLabel"), data: rows.map(() => 70), borderColor: palette.critical, borderWidth: 0.8, borderDash: [4, 4], pointRadius: 0 },
          { label: t("oversoldLabel"), data: rows.map(() => 30), borderColor: palette.good, borderWidth: 0.8, borderDash: [4, 4], pointRadius: 0 },
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
    state.lastGainers = rows;
    renderTopGainers(rows);
  } catch (err) {
    state.lastGainers = null;
    container.innerHTML = `<p class="gainers-status">${t("gainersError")}</p>`;
  }
}

function renderTopGainers(rows) {
  const container = document.getElementById("top-gainers-list");
  container.innerHTML = "";
  if (!rows || !rows.length) {
    container.innerHTML = `<p class="gainers-status">${t("gainersEmpty")}</p>`;
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
      <button class="gainer-add-btn" type="button" title="${t("addToSelected")}">+</button>
    `;
    card.querySelector(".gainer-add-btn").addEventListener("click", () => {
      state.selected[row.name] = row.symbol;
      renderTickerList();
    });
    container.appendChild(card);
  });
}

updatePortfolioAccess();
renderTickerList();
loadTopGainers();
if (canUseCartera) loadTransactionsFromServer();
