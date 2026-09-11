"""Cálculo de rendimiento de cartera a partir de un histórico de movimientos (aportaciones y
retiradas) por instrumento, no de una única compra. Cada movimiento suma o resta un número de
participaciones directamente (positivo = aportación, negativo = retirada), y el valor de la
cartera en el tiempo se construye acumulando esas participaciones. También calcula una cartera
"espejo" invirtiendo en el benchmark el importe en euros equivalente de cada movimiento (unidades
de fondos distintos no son comparables entre sí ni con las del índice), para comparar de forma
justa cómo le habría ido a ese mismo dinero en el índice."""

import pandas as pd


def _entry_price(close: pd.Series, date: pd.Timestamp) -> tuple[pd.Timestamp, float] | None:
    """Primer precio de cierre disponible en `date` o después."""
    close = close.dropna()
    if close.empty:
        return None
    idx = close.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)
    mask = idx >= date
    if not mask.any():
        return None
    pos = mask.argmax()
    return close.index[pos], float(close.iloc[pos])


def _share_series_by_units(
    close: pd.Series, transactions: list[dict]
) -> tuple[pd.Series | None, float, float, list[dict]]:
    """Construye la serie de participaciones acumuladas a partir de movimientos que ya vienen en
    participaciones (`units`), procesados en orden de fecha. Devuelve (serie de participaciones
    alineada con `close`, participaciones actuales, importe neto invertido en euros, lista de
    eventos {amount, date} en euros para poder simular esos mismos importes en el benchmark) — o
    (None, 0, 0, []) si ningún movimiento fue válido."""
    ordered = sorted(transactions, key=lambda t: t["date"])
    steps = []
    cumulative = 0.0
    net_invested = 0.0
    invested_events = []

    for tx in ordered:
        entry = _entry_price(close, pd.Timestamp(tx["date"]))
        if entry is None or entry[1] <= 0:
            continue
        entry_date, price = entry
        units = tx["units"]
        euro_amount = units * price
        cumulative += units
        net_invested += euro_amount
        steps.append((entry_date, cumulative))
        invested_events.append({"amount": euro_amount, "date": entry_date.strftime("%Y-%m-%d")})

    if not steps:
        return None, 0.0, 0.0, []

    step_series = pd.Series([v for _, v in steps], index=pd.DatetimeIndex([d for d, _ in steps]))
    step_series = step_series[~step_series.index.duplicated(keep="last")].sort_index()
    shares_series = step_series.reindex(close.index).ffill().fillna(0)
    return shares_series, cumulative, net_invested, invested_events


def _share_series_by_amount(close: pd.Series, transactions: list[dict]) -> tuple[pd.Series | None, float, float]:
    """Igual que `_share_series_by_units` pero a partir de movimientos en euros (`amount`), que se
    convierten a participaciones dividiendo por el precio de entrada. Se usa para simular la
    cartera "espejo" en el benchmark a partir de los importes en euros de los movimientos reales."""
    ordered = sorted(transactions, key=lambda t: t["date"])
    steps = []
    cumulative = 0.0
    net_invested = 0.0

    for tx in ordered:
        entry = _entry_price(close, pd.Timestamp(tx["date"]))
        if entry is None or entry[1] <= 0:
            continue
        entry_date, price = entry
        cumulative += tx["amount"] / price
        net_invested += tx["amount"]
        steps.append((entry_date, cumulative))

    if not steps:
        return None, 0.0, 0.0

    step_series = pd.Series([v for _, v in steps], index=pd.DatetimeIndex([d for d, _ in steps]))
    step_series = step_series[~step_series.index.duplicated(keep="last")].sort_index()
    shares_series = step_series.reindex(close.index).ffill().fillna(0)
    return shares_series, cumulative, net_invested


def compute_holding(
    name: str, symbol: str, transactions: list[dict], close: pd.Series
) -> tuple[dict | None, list[dict]]:
    """transactions: [{units, date}, ...]. Devuelve (resultado, eventos en euros para el
    benchmark) — (None, []) si no hay ningún movimiento válido."""
    shares_series, current_shares, net_invested, invested_events = _share_series_by_units(close, transactions)
    if shares_series is None or net_invested == 0:
        return None, []

    current_price = float(close.dropna().iloc[-1])
    current_value = current_shares * current_price

    result = {
        "name": name,
        "symbol": symbol,
        "invested": net_invested,
        "n_transactions": len(transactions),
        "current_price": current_price,
        "current_value": current_value,
        "gain_abs": current_value - net_invested,
        "gain_pct": (current_value / net_invested - 1) * 100 if net_invested else None,
        "series": shares_series * close,
    }
    return result, invested_events


def compute_benchmark_holding(name: str, symbol: str, amount_transactions: list[dict], close: pd.Series) -> dict | None:
    """amount_transactions: [{amount, date}, ...] en euros (la simulación "espejo")."""
    shares_series, current_shares, net_invested = _share_series_by_amount(close, amount_transactions)
    if shares_series is None or net_invested == 0:
        return None

    current_price = float(close.dropna().iloc[-1])
    current_value = current_shares * current_price

    return {
        "name": name,
        "symbol": symbol,
        "invested": net_invested,
        "current_price": current_price,
        "current_value": current_value,
        "gain_abs": current_value - net_invested,
        "gain_pct": (current_value / net_invested - 1) * 100 if net_invested else None,
        "series": shares_series * close,
    }


def compute_portfolio(
    holdings_input: list[dict],
    closes: dict[str, pd.Series],
    benchmark_close: pd.Series | None,
    benchmark_name: str,
) -> dict | None:
    """holdings_input: [{name, symbol, transactions: [{units, date}, ...]}, ...]"""
    holdings = []
    skipped = []
    all_series = []
    benchmark_tx = []  # importes en euros de todos los movimientos de todos los fondos, para el espejo

    for h in holdings_input:
        name = h.get("name") or h.get("symbol") or "?"
        symbol = h.get("symbol")
        txs = h.get("transactions") or []

        if not symbol or not txs:
            skipped.append(name)
            continue

        close = closes.get(symbol)
        if close is None:
            skipped.append(name)
            continue

        result, invested_events = compute_holding(name, symbol, txs, close)
        if result is None:
            skipped.append(name)
            continue

        all_series.append(result.pop("series"))
        holdings.append(result)
        benchmark_tx.extend(invested_events)

    if not holdings:
        return None

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
    benchmark_series = None
    if benchmark_close is not None and benchmark_tx:
        bench_result = compute_benchmark_holding(benchmark_name, benchmark_name, benchmark_tx, benchmark_close)
        if bench_result is not None:
            benchmark_series = bench_result["series"]
            bench_current = bench_result["current_value"]
            benchmark_totals = {
                "name": benchmark_name,
                "current_value": bench_current,
                "gain_abs": bench_current - total_invested,
                "gain_pct": (bench_current / total_invested - 1) * 100 if total_invested else None,
            }

    # Índice común a todas las series (unión de fechas), para sumar los fondos entre sí y
    # compararlos con el benchmark sin desalinear las fechas de cada uno.
    master_index = all_series[0].index
    for series in all_series[1:]:
        master_index = master_index.union(series.index)
    if benchmark_series is not None:
        master_index = master_index.union(benchmark_series.index)
    master_index = master_index.sort_values()

    def _align(series: pd.Series) -> pd.Series:
        return series.reindex(master_index).ffill().fillna(0)

    portfolio_series = None
    for series in all_series:
        aligned = _align(series)
        portfolio_series = aligned if portfolio_series is None else portfolio_series + aligned

    benchmark_aligned = _align(benchmark_series) if benchmark_series is not None else None

    series_records = []
    for i, date in enumerate(master_index):
        record = {"date": pd.Timestamp(date).strftime("%Y-%m-%d"), "portfolio": float(portfolio_series.iloc[i])}
        if benchmark_aligned is not None:
            record["benchmark"] = float(benchmark_aligned.iloc[i])
        series_records.append(record)

    return {
        "holdings": holdings,
        "totals": totals,
        "benchmark": benchmark_totals,
        "series": series_records,
        "skipped": skipped,
    }
