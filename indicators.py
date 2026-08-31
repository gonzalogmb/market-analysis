"""Indicadores técnicos y estadísticos sobre series de precios, con pandas."""

import numpy as np
import pandas as pd

TRADING_DAYS_YEAR = 252


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window).mean()


def ema(close: pd.Series, window: int) -> pd.Series:
    return close.ewm(span=window, adjust=False).mean()


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def rolling_volatility(close: pd.Series, window: int = 20) -> pd.Series:
    """Volatilidad anualizada (%) de los retornos diarios, en ventana móvil."""
    returns = close.pct_change()
    return returns.rolling(window).std() * np.sqrt(TRADING_DAYS_YEAR) * 100


def add_indicators(df: pd.DataFrame, sma_windows: tuple[int, ...] = (20, 50), rsi_window: int = 14) -> pd.DataFrame:
    df = df.copy()
    for window in sma_windows:
        df[f"SMA{window}"] = sma(df["Close"], window)
    df["EMA20"] = ema(df["Close"], 20)
    df[f"RSI{rsi_window}"] = rsi(df["Close"], rsi_window)
    df["Volatilidad %"] = rolling_volatility(df["Close"])
    return df


def annualized_return(close: pd.Series) -> float | None:
    """Retorno geométrico anualizado entre el primer y el último precio de la serie."""
    close = close.dropna()
    if len(close) < 2:
        return None
    total_return = close.iloc[-1] / close.iloc[0] - 1
    days = (close.index[-1] - close.index[0]).days
    if days <= 0:
        return None
    years = days / 365.25
    return ((1 + total_return) ** (1 / years) - 1) * 100


def annualized_volatility(close: pd.Series) -> float | None:
    returns = close.pct_change().dropna()
    if returns.empty:
        return None
    return returns.std() * np.sqrt(TRADING_DAYS_YEAR) * 100


def sharpe_ratio(close: pd.Series, risk_free_rate: float = 0.0) -> float | None:
    returns = close.pct_change().dropna()
    if returns.empty or returns.std() == 0:
        return None
    excess = returns - risk_free_rate / TRADING_DAYS_YEAR
    return (excess.mean() / returns.std()) * np.sqrt(TRADING_DAYS_YEAR)


def max_drawdown(close: pd.Series) -> float | None:
    if close.empty:
        return None
    cumulative_max = close.cummax()
    drawdown = close / cumulative_max - 1
    return drawdown.min() * 100


def stats_summary(histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Estadísticas anualizadas por instrumento sobre todo el histórico descargado."""
    rows = []
    for name, df in histories.items():
        close = df["Close"]
        rows.append(
            {
                "Nombre": name,
                "Retorno anualizado %": annualized_return(close),
                "Volatilidad anualizada %": annualized_volatility(close),
                "Sharpe": sharpe_ratio(close),
                "Máx drawdown %": max_drawdown(close),
            }
        )
    return pd.DataFrame(rows).set_index("Nombre")


def correlation_matrix(histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Matriz de correlación entre los retornos diarios de cada instrumento, alineados por fecha."""
    closes = {}
    for name, df in histories.items():
        close = df["Close"].copy()
        close.index = pd.to_datetime(close.index.date)
        closes[name] = close

    combined = pd.DataFrame(closes)
    returns = combined.pct_change()
    return returns.corr()
