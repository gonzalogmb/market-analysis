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
- [`portfolio.py`](portfolio.py) — cálculo de rendimiento de cartera a partir de posiciones reales (importe invertido + fecha de compra):
  - `compute_holding(name, symbol, invested, purchase_date, close)`: convierte un importe invertido en participaciones a partir del primer precio disponible en la fecha de compra (o después), y calcula precio de entrada, valor actual y ganancia €/%.
  - `compute_portfolio(holdings_input, closes, benchmark_close, benchmark_name)`: agrega todas las posiciones (alineando las series por fecha, con relleno hacia delante) para obtener el valor total de la cartera a lo largo del tiempo, y construye una cartera "espejo" invirtiendo los mismos importes y fechas en un benchmark, para comparar de forma justa cómo le habría ido a ese dinero en el índice.
- [`indicators.py`](indicators.py) — indicadores técnicos y estadísticos sobre series de precios:
  - `sma(close, window)` / `ema(close, window)`: medias móviles simple/exponencial.
  - `rsi(close, window=14)`: índice de fuerza relativa.
  - `rolling_volatility(close, window=20)`: volatilidad anualizada (%) en ventana móvil.
  - `add_indicators(df)`: añade SMA20/SMA50, EMA20, RSI14 y volatilidad móvil a un `DataFrame` OHLCV.
  - `annualized_return(close)` / `annualized_volatility(close)` / `sharpe_ratio(close)` / `max_drawdown(close)`: métricas sobre todo el periodo descargado (retorno anualizado calculado de forma geométrica).
  - `stats_summary(histories)`: `DataFrame` con esas métricas para todos los instrumentos.
  - `correlation_matrix(histories)`: matriz de correlación entre los retornos diarios de los instrumentos, alineados por fecha.
- [`db.py`](db.py) — persistencia de la cartera en Postgres (Neon, Supabase o similar), vía la variable de entorno `DATABASE_URL`. Al ser una app de un único usuario, la tabla `portfolio_holdings` no tiene columna de usuario: `save_holdings(holdings)` reemplaza su contenido completo en cada guardado y `load_holdings()` lo devuelve.
- [`server.py`](server.py) — backend web con [Flask](https://flask.palletsprojects.com/): sirve la página (`templates/index.html`) y expone la API JSON que la usa —
  - `GET/POST /login`, `POST /logout`: login con una única contraseña (`APP_PASSWORD`), guardada en la cookie de sesión firmada con `SECRET_KEY`. Si `APP_PASSWORD` no está definida, el login queda desactivado (todas las rutas quedan abiertas — útil para desarrollo local rápido). Tras 3 intentos fallidos desde la misma IP, el login se bloquea 5 horas (el contador se guarda en la tabla `login_attempts` de Postgres, así que el bloqueo persiste aunque el servidor reinicie).
  - `GET /api/search?q=...`: autocompletado de instrumentos vía `search_symbols` de Yahoo Finance.
  - `POST /api/generate`: recibe `{tickers, range, interval}` y devuelve resumen, estadísticas, correlación e históricos (con indicadores) en JSON, listos para pintar en el navegador.
  - `POST /api/portfolio`: recibe `{holdings: [{name, symbol, invested, date}, ...]}` y devuelve, en EUR, el valor y ganancia de cada posición, los totales de la cartera, una cartera "espejo" en el S&P 500 (mismos importes/fechas) para comparar, y la serie temporal de ambas para el gráfico. Cuando un instrumento cotiza en otra divisa, se convierte a EUR con el tipo de cambio histórico de Yahoo Finance; si no se puede obtener ese tipo de cambio, se avisa en `currency_warnings` y el importe se deja sin convertir.
  - `GET /api/portfolio/holdings`, `PUT /api/portfolio/holdings`: cargar y guardar (reemplazando todo) las posiciones de la cartera en la base de datos.
- [`templates/index.html`](templates/index.html) / [`static/`](static/) — UI web: barra lateral para buscar y seleccionar instrumentos (con autocompletado), rango e intervalo, y una sección **Mi cartera** para introducir importe invertido y fecha de compra por instrumento; panel principal con pestañas Resumen / Estadísticas / Correlación / Gráficos / Mi cartera. Los gráficos de precio+SMA/EMA/RSI y el de cartera vs S&P 500 se dibujan en el navegador con [Chart.js](https://www.chartjs.org/) (interactivos: tooltip, leyenda) y el heatmap de correlación como una cuadrícula HTML/CSS coloreada por valor. Los importes y fechas de "Mi cartera" se guardan en la base de datos del servidor (no en el navegador), así que persisten igual entre dispositivos.

## Uso

```bash
python server.py
```

Se abre en `http://localhost:5000`. En la barra lateral ves los instrumentos seleccionados (quitables con ✕), buscas otros por nombre o ticker con autocompletado en vivo, y eliges rango/intervalo. Al pulsar **Generar** se descargan los datos y se muestran en pestañas: resumen (tarjetas con precio y variación %), estadísticas anualizadas, heatmap de correlación y gráficos interactivos de precio/RSI por instrumento.

### Mi cartera

En la sección **Mi cartera** de la barra lateral, para cada instrumento seleccionado puedes indicar cuánto invertiste y en qué fecha; se guarda automáticamente en el servidor (con un pequeño retraso tras dejar de escribir). Al pulsar **Calcular cartera** se muestra, en la pestaña *Mi cartera*: el total invertido, el valor actual y la ganancia €/% de cada posición y del conjunto, cómo le habría ido a ese mismo dinero invertido en el S&P 500 en las mismas fechas, y un gráfico con la evolución de ambas carteras en el tiempo.

### Login y variables de entorno

La app admite proteger todo el sitio con una única contraseña y guardar la cartera en una base de datos Postgres. Copia [`.env.example`](.env.example) a `.env` (no se sube a git) y rellena:

- `APP_PASSWORD`: la contraseña para entrar. Si la dejas vacía, no hay login (útil en local).
- `SECRET_KEY`: cualquier cadena larga y aleatoria, para firmar la cookie de sesión.
- `DATABASE_URL`: cadena de conexión a una Postgres. Para tener una gratis en minutos:
  1. Crea una cuenta en [neon.tech](https://neon.tech) (o [supabase.com](https://supabase.com)) y un proyecto nuevo.
  2. Copia la "connection string" que te dan (formato `postgresql://usuario:contraseña@host/basededatos`) en `DATABASE_URL`.
  3. La tabla se crea sola la primera vez que arranca el servidor.

En Render, configura estas mismas variables en el dashboard del servicio (Settings → Environment) en vez de en un `.env`.

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
