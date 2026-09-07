"""Cálculo de rendimiento de cartera: convierte importes invertidos en participaciones a partir
de una fecha de compra y agrega el valor de todas las posiciones a lo largo del tiempo. También
calcula una cartera "espejo" invirtiendo los mismos importes y fechas en un benchmark, para poder
comparar de forma justa cómo le habría ido a ese mismo dinero en el índice."""

import pandas as pd


def _entry_price(close: pd.Series, purchase_date: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    """Primer precio de cierre disponible en la fecha de compra o después."""
    close = close.dropna()
    if close.empty:
        return None
    idx = close.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    mask = idx >= purchase_date
    if not mask.any():
        return None
    pos = mask.argmax()
    return close.index[pos], float(close.iloc[pos])


def compute_holding(name: str, symbol: str, invested: float, purchase_date: pd.Timestamp, close: pd.Series) -> dict | None:
    entry = _entry_price(close, purchase_date)
    if entry is None or entry[1] <= 0:
        return None
    entry_date, entry_price = entry

    close_clean = close.dropna()
    current_price = float(close_clean.iloc[-1])
    shares = invested / entry_price
    current_value = shares * current_price

    return {
        "name": name,
        "symbol": symbol,
        "invested": invested,
        "date": str(purchase_date.date()),
        "entry_date": str(pd.Timestamp(entry_date).date()),
        "entry_price": entry_price,
        "current_price": current_price,
        "current_value": current_value,
        "gain_abs": current_value - invested,
        "gain_pct": (current_value / invested - 1) * 100,
        "series": close.loc[close.index >= entry_date] * shares,
    }


def compute_portfolio(
    holdings_input: list[dict],
    closes: dict[str, pd.Series],
    benchmark_close: pd.Series | None,
    benchmark_name: str,
) -> dict | None:
    """holdings_input: [{name, symbol, invested, date}], closes: {symbol: Serie de cierres (misma
    divisa base para todos), ya convertida}. Devuelve None si ninguna posición pudo calcularse."""
    holding_results = []
    bench_series_list = []
    skipped = []

    for h in holdings_input:
        name = h.get("name") or h.get("symbol") or "?"
        symbol = h.get("symbol")
        invested = h.get("invested")
        date = h.get("date")

        if not symbol or not date or not invested or invested <= 0:
            skipped.append(name)
            continue

        close = closes.get(symbol)
        if close is None:
            skipped.append(name)
            continue

        try:
            purchase_date = pd.Timestamp(date)
        except (ValueError, TypeError):
            skipped.append(name)
            continue

        result = compute_holding(name, symbol, float(invested), purchase_date, close)
        if result is None:
            skipped.append(name)
            continue

        holding_results.append(result)

        if benchmark_close is not None:
            bench = compute_holding(name, benchmark_name, float(invested), purchase_date, benchmark_close)
            if bench is not None:
                bench_series_list.append(bench["series"])

    if not holding_results:
        return None

    # Índice común a todas las series (unión de fechas). Cada serie se rellena hacia delante sobre
    # ese índice: 0 antes de su propia fecha de entrada, último precio conocido en los huecos
    # posteriores (fines de semana, festivos, o instrumentos con cotización menos frecuente). Sumar
    # directamente con fill_value=0 sin este paso pondría a cero una posición en cualquier fecha en
    # la que su serie no tuviera un punto exacto, en vez de arrastrar su último valor.
    all_series = [h["series"] for h in holding_results] + bench_series_list
    master_index = all_series[0].index
    for series in all_series[1:]:
        master_index = master_index.union(series.index)
    master_index = master_index.sort_values()

    def _align(series: pd.Series) -> pd.Series:
        return series.reindex(master_index).ffill().fillna(0)

    portfolio_series = None
    for h in holding_results:
        aligned = _align(h.pop("series"))
        portfolio_series = aligned if portfolio_series is None else portfolio_series + aligned

    benchmark_series = None
    for series in bench_series_list:
        aligned = _align(series)
        benchmark_series = aligned if benchmark_series is None else benchmark_series + aligned

    holdings = holding_results

    total_invested = sum(h["invested"] for h in holdings)
    total_current = sum(h["current_value"] for h in holdings)
    for h in holdings:
        h["weight_pct"] = h["invested"] / total_invested * 100 if total_invested else None

    totals = {
        "invested": total_invested,
        "current_value": total_current,
        "gain_abs": total_current - total_invested,
        "gain_pct": (total_current / total_invested - 1) * 100 if total_invested else None,
    }

    benchmark_totals = None
    if benchmark_series is not None and not benchmark_series.dropna().empty:
        bench_current = float(benchmark_series.dropna().iloc[-1])
        benchmark_totals = {
            "name": benchmark_name,
            "current_value": bench_current,
            "gain_abs": bench_current - total_invested,
            "gain_pct": (bench_current / total_invested - 1) * 100 if total_invested else None,
        }

    series_records = []
    for i, date in enumerate(master_index):
        record = {"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "portfolio": float(portfolio_series.iloc[i])}
        if benchmark_series is not None:
            record["benchmark"] = float(benchmark_series.iloc[i])
        series_records.append(record)

    return {
        "holdings": holdings,
        "totals": totals,
        "benchmark": benchmark_totals,
        "series": series_records,
        "skipped": skipped,
    }
