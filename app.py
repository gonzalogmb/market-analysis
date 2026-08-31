"""UI interactiva (Streamlit) para seleccionar instrumentos y ver los gráficos generados."""

from pathlib import Path

import streamlit as st

from fetch_yahoo_data import TICKERS, fetch_history, fetch_summary, search_symbols
from indicators import correlation_matrix, stats_summary
from visualization import plot_correlation_heatmap, plot_instrument, save_charts

RANGES = ["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"]
INTERVALS = ["1d", "1wk", "1mo"]

st.set_page_config(page_title="Market Analysis", layout="wide")
st.title("📈 Market Analysis")

@st.cache_data(ttl=300, show_spinner=False)
def cached_search(query: str) -> list[dict]:
    return search_symbols(query)


if "manual_tickers" not in st.session_state:
    st.session_state["manual_tickers"] = {}

with st.sidebar:
    st.header("Selección")

    selected_defaults = st.multiselect(
        "Instrumentos por defecto",
        options=list(TICKERS.keys()),
        default=list(TICKERS.keys()),
    )

    st.caption("Buscar instrumento en Yahoo Finance")
    query = st.text_input("Buscar", placeholder="ej. Apple, oro, S&P 500...", label_visibility="collapsed")

    if query.strip():
        matches = cached_search(query)
        if matches:
            options = {f"{m['name']} — {m['symbol']} ({m['exchange']}, {m['type']})": m for m in matches}
            choice_label = st.selectbox("Resultados", list(options.keys()))
            if st.button("+ Añadir", use_container_width=True):
                chosen = options[choice_label]
                st.session_state["manual_tickers"][chosen["name"]] = chosen["symbol"]
        else:
            st.caption("Sin resultados para esa búsqueda.")

    if st.session_state["manual_tickers"]:
        st.caption("Añadidos manualmente")
        for name, symbol in list(st.session_state["manual_tickers"].items()):
            col_name, col_remove = st.columns([4, 1])
            col_name.write(f"{name} ({symbol})")
            if col_remove.button("✕", key=f"remove_{symbol}"):
                del st.session_state["manual_tickers"][name]
                st.rerun()

    range_ = st.selectbox("Rango histórico", RANGES, index=RANGES.index("6mo"))
    interval = st.selectbox("Intervalo", INTERVALS, index=0)

    save_pngs = st.checkbox("Guardar PNGs en charts/", value=False)

    run = st.button("Generar", type="primary", use_container_width=True)

if "result" not in st.session_state:
    st.session_state["result"] = None

if run:
    tickers = {name: TICKERS[name] for name in selected_defaults}
    tickers.update(st.session_state["manual_tickers"])

    if not tickers:
        st.warning("Selecciona al menos un instrumento.")
    else:
        with st.spinner("Descargando datos de Yahoo Finance..."):
            try:
                summary = fetch_summary(tickers)
                histories = fetch_history(tickers, range_=range_, interval=interval)
                stats = stats_summary(histories)
                corr = correlation_matrix(histories) if len(histories) > 1 else None
            except Exception as exc:  # noqa: BLE001
                st.error(f"Error al descargar datos: {exc}")
                st.session_state["result"] = None
            else:
                st.session_state["result"] = {
                    "summary": summary,
                    "histories": histories,
                    "stats": stats,
                    "corr": corr,
                }
                if save_pngs:
                    saved = save_charts(histories, corr, Path("charts"))
                    st.success(f"Gráficos guardados en charts/ ({len(saved)} archivos)")

result = st.session_state["result"]

if result is None:
    st.info("Elige instrumentos en la barra lateral y pulsa **Generar**.")
else:
    st.subheader("Resumen")
    st.dataframe(result["summary"], use_container_width=True)

    st.subheader("Estadísticas anualizadas")
    st.dataframe(result["stats"], use_container_width=True)

    if result["corr"] is not None:
        st.subheader("Correlación entre retornos diarios")
        col1, col2 = st.columns([2, 1])
        with col1:
            st.pyplot(plot_correlation_heatmap(result["corr"]), use_container_width=False)
        with col2:
            st.dataframe(result["corr"].round(2), use_container_width=True)

    st.subheader("Gráficos por instrumento")
    items = list(result["histories"].items())
    for i in range(0, len(items), 2):
        row = st.columns(2)
        for col, (name, df) in zip(row, items[i : i + 2]):
            with col:
                st.pyplot(plot_instrument(df, name), use_container_width=True)
