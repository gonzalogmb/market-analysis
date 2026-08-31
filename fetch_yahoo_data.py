"""Consulta datos de mercado directamente en la API REST de Yahoo Finance (sin yfinance) y los expone como DataFrames de pandas."""

import sys

import pandas as pd
import requests

from indicators import add_indicators

sys.stdout.reconfigure(encoding="utf-8")

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TICKERS = {
    "S&P 500": "^GSPC",
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
    quote = result["indicators"]["quote"][0]
    df = pd.DataFrame(
        {
            "Open": quote["open"],
            "High": quote["high"],
            "Low": quote["low"],
            "Close": quote["close"],
            "Volume": quote["volume"],
        },
        index=pd.to_datetime(result["timestamp"], unit="s", utc=True),
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


def combine_history(histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
    by_date = {}
    for name, df in histories.items():
        df = df.copy()
        df.index = pd.to_datetime(df.index.date)
        df.index.name = "Date"
        by_date[name] = df

    combined = pd.concat(by_date.values(), keys=by_date.keys(), axis=1)
    combined.columns.names = ["Nombre", "Campo"]
    return combined


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
