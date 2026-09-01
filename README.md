# market-analysis

Herramienta en Python para consultar datos de mercado (índices y fondos de inversión) directamente desde la API pública de Yahoo Finance, sin depender de la librería `yfinance`, y analizarlos con `pandas` (indicadores técnicos, estadísticas anualizadas y correlaciones), con una UI web para explorarlos.

## Estructura

- [`fetch_yahoo_data.py`](fetch_yahoo_data.py) — módulo de datos:
  - `fetch_chart(symbol, range_, interval)`: llama al endpoint `query1.finance.yahoo.com/v8/finance/chart/{symbol}` y devuelve el JSON crudo.
  - `chart_to_dataframe(result)`: convierte la respuesta de Yahoo en un `DataFrame` OHLCV indexado por fecha.
  - `search_symbols(query, count=8)`: busca instrumentos en Yahoo Finance por nombre o ticker (autocompletado).
  - `fetch_history(tickers, range_, interval, with_indicators=True)`: devuelve un `dict[nombre, DataFrame]` con el histórico de cada instrumento (`Retorno %` + indicadores técnicos de `indicators.py`).
  - `fetch_summary(tickers)`: `DataFrame` con precio actual, cierre anterior, variación %, y máximo/mínimo de 52 semanas por instrumento.
  - `TICKERS`: diccionario por defecto con los instrumentos seguidos (S&P 500, MyInvestor Value Clase C, DJE Gold & Ressourcen PA EUR Dis).
- [`indicators.py`](indicators.py) — indicadores técnicos y estadísticos sobre series de precios:
  - `sma(close, window)` / `ema(close, window)`: medias móviles simple/exponencial.
  - `rsi(close, window=14)`: índice de fuerza relativa.
  - `rolling_volatility(close, window=20)`: volatilidad anualizada (%) en ventana móvil.
  - `add_indicators(df)`: añade SMA20/SMA50, EMA20, RSI14 y volatilidad móvil a un `DataFrame` OHLCV.
  - `annualized_return(close)` / `annualized_volatility(close)` / `sharpe_ratio(close)` / `max_drawdown(close)`: métricas sobre todo el periodo descargado (retorno anualizado calculado de forma geométrica).
  - `stats_summary(histories)`: `DataFrame` con esas métricas para todos los instrumentos.
  - `correlation_matrix(histories)`: matriz de correlación entre los retornos diarios de los instrumentos, alineados por fecha.
- [`server.py`](server.py) — backend web con [Flask](https://flask.palletsprojects.com/): sirve la página (`templates/index.html`) y expone la API JSON que la usa —
  - `GET /api/search?q=...`: autocompletado de instrumentos vía `search_symbols` de Yahoo Finance.
  - `POST /api/generate`: recibe `{tickers, range, interval}` y devuelve resumen, estadísticas, correlación e históricos (con indicadores) en JSON, listos para pintar en el navegador.
- [`templates/index.html`](templates/index.html) / [`static/`](static/) — UI web: barra lateral para buscar y seleccionar instrumentos (con autocompletado), rango e intervalo; panel principal con pestañas Resumen / Estadísticas / Correlación / Gráficos. Los gráficos de precio+SMA/EMA/RSI se dibujan en el navegador con [Chart.js](https://www.chartjs.org/) (interactivos: tooltip, leyenda) y el heatmap de correlación como una cuadrícula HTML/CSS coloreada por valor.

## Uso

```bash
python server.py
```

Se abre en `http://localhost:5000`. En la barra lateral ves los instrumentos seleccionados (quitables con ✕), buscas otros por nombre o ticker con autocompletado en vivo, y eliges rango/intervalo. Al pulsar **Generar** se descargan los datos y se muestran en pestañas: resumen (tarjetas con precio y variación %), estadísticas anualizadas, heatmap de correlación y gráficos interactivos de precio/RSI por instrumento.

## Instrumentos por defecto

| Nombre | Ticker Yahoo Finance |
|---|---|
| S&P 500 | `^GSPC` |
| MyInvestor Value Clase C | `0P0001T8V7.F` (ISIN ES0165243025) |
| DJE Gold & Ressourcen PA (EUR) Dis | `0P00000HTQ.F` (ISIN LU0159550077) |

## Requisitos

```bash
pip install pandas numpy requests flask
```
