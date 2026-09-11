"""Consulta datos de mercado directamente en la API REST de Yahoo Finance (sin yfinance) y los expone como DataFrames de pandas."""

import sys

import pandas as pd
import requests

from indicators import add_indicators

sys.stdout.reconfigure(encoding="utf-8")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
SCREENER_URL = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TICKERS = {
    "MyInvestor Value Clase C": "0P0001T8V7.F",
    "DJE Gold & Ressourcen PA (EUR) Dis": "0P00000HTQ.F",
}


def fetch_chart(symbol: str, range_: str = "5d", interval: str = "1d") -> dict:
    params = {"range": range_, "interval": interval}
    response = requests.get(
        CHART_URL.format(symbol=symbol), params=params, headers=HEADERS, timeout=10
    )
    response.raise_for_status()
    payload = response.json()

    error = payload["chart"]["error"]
    if error:
        raise ValueError(f"Yahoo Finance error para {symbol}: {error}")

    return payload["chart"]["result"][0]


def chart_to_dataframe(result: dict) -> pd.DataFrame:
    """Algunos símbolos (sobre todo fondos listados en bolsas alemanas, p.ej. sufijo .SG/.F) traen
    en Yahoo Finance un histórico incompleto que no incluye open/high/low/volume para todas las
    fechas, o directamente ninguno de esos campos. Solo necesitamos el cierre, así que el resto se
    trata como opcional en vez de asumir que siempre viene."""
    quote = result["indicators"]["quote"][0]
    index = pd.to_datetime(result["timestamp"], unit="s", utc=True)
    n = len(index)

    def _column(key):
        values = quote.get(key)
        return values if values is not None else [None] * n

    df = pd.DataFrame(
        {
            "Open": _column("open"),
            "High": _column("high"),
            "Low": _column("low"),
            "Close": _column("close"),
            "Volume": _column("volume"),
        },
        index=index,
    )
    df.index.name = "Date"
    tz = result["meta"].get("exchangeTimezoneName")
    if tz:
        df.index = df.index.tz_convert(tz)
    return df.dropna(subset=["Close"])


def search_symbols(query: str, count: int = 8) -> list[dict]:
    """Busca instrumentos válidos en Yahoo Finance por nombre o ticker (autocompletado)."""
    query = query.strip()
    if len(query) < 2:
        return []

    params = {"q": query, "quotesCount": count, "newsCount": 0}
    try:
        response = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    results = []
    for quote in payload.get("quotes", []):
        symbol = quote.get("symbol")
        if not symbol:
            continue
        results.append(
            {
                "symbol": symbol,
                "name": quote.get("shortname") or quote.get("longname") or symbol,
                "exchange": quote.get("exchange", ""),
                "type": quote.get("quoteType", ""),
            }
        )
    return results


def fetch_top_gainers(count: int = 10) -> list[dict]:
    """Acciones que más suben en el día (screener 'Day Gainers' de Yahoo Finance)."""
    params = {"count": max(count, 25), "scrIds": "day_gainers", "lang": "en-US", "region": "US"}
    try:
        response = requests.get(SCREENER_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    results = payload.get("finance", {}).get("result") or []
    if not results:
        return []

    quotes = results[0].get("quotes", [])
    quotes.sort(key=lambda q: q.get("regularMarketChangePercent") or 0, reverse=True)

    top = []
    for quote in quotes[:count]:
        symbol = quote.get("symbol")
        if not symbol:
            continue
        top.append(
            {
                "symbol": symbol,
                "name": quote.get("shortName") or quote.get("longName") or symbol,
                "price": quote.get("regularMarketPrice"),
                "change_percent": quote.get("regularMarketChangePercent"),
                "currency": quote.get("currency"),
            }
        )
    return top


BASE_CURRENCY = "EUR"
FULL_HISTORY_RANGE = "20y"  # Con range="max" Yahoo degrada el intervalo a datos trimestrales.


def fetch_full_history_meta(symbol: str) -> tuple[pd.Series, str]:
    """Cierres diarios de los últimos ~20 años (o desde que cotiza, si es menos) y la moneda nativa."""
    result = fetch_chart(symbol, range_=FULL_HISTORY_RANGE, interval="1d")
    close = chart_to_dataframe(result)["Close"].copy()
    close.index = pd.to_datetime(close.index.date)
    close = close[~close.index.duplicated(keep="last")].sort_index()
    currency = result["meta"].get("currency") or BASE_CURRENCY
    return close, currency


def fetch_full_close_in_base(symbol: str, base: str = BASE_CURRENCY) -> tuple[pd.Series, bool]:
    """Cierres diarios de `symbol` convertidos a `base` (por defecto EUR) con el tipo de cambio
    histórico de Yahoo Finance. Devuelve (serie, convertida) — `convertida` es False si el
    instrumento ya estaba en `base` o si no se pudo obtener el tipo de cambio (se devuelve sin
    convertir en ese caso, para no perder el dato)."""
    close, currency = fetch_full_history_meta(symbol)
    if currency == base:
        return close, True

    try:
        fx, _ = fetch_full_history_meta(f"{currency}{base}=X")
    except (requests.RequestException, ValueError, KeyError):
        return close, False

    fx = fx.reindex(close.index.union(fx.index)).sort_index().ffill().reindex(close.index)
    if fx.isna().all():
        return close, False
    return close * fx, True


def fetch_history(
    tickers: dict[str, str], range_: str = "5d", interval: str = "1d", with_indicators: bool = True
) -> dict[str, pd.DataFrame]:
    histories = {}
    for name, symbol in tickers.items():
        df = chart_to_dataframe(fetch_chart(symbol, range_, interval))
        df["Retorno %"] = df["Close"].pct_change() * 100
        if with_indicators:
            df = add_indicators(df)
        histories[name] = df
    return histories


def fetch_summary(tickers: dict[str, str]) -> pd.DataFrame:
    rows = []
    for name, symbol in tickers.items():
        meta = fetch_chart(symbol)["meta"]
        precio = meta.get("regularMarketPrice")
        cierre_anterior = meta.get("chartPreviousClose")
        variacion = (precio / cierre_anterior - 1) * 100 if precio and cierre_anterior else None
        rows.append(
            {
                "Nombre": name,
                "Ticker": symbol,
                "Precio": precio,
                "Moneda": meta.get("currency"),
                "Cierre anterior": cierre_anterior,
                "Variación %": variacion,
                "Máx 52 sem": meta.get("fiftyTwoWeekHigh"),
                "Mín 52 sem": meta.get("fiftyTwoWeekLow"),
            }
        )
    return pd.DataFrame(rows).set_index("Nombre")
