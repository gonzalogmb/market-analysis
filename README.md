# market-analysis

Herramienta en Python para consultar datos de mercado (índices y fondos de inversión) directamente desde la API pública de Yahoo Finance, sin depender de la librería `yfinance`, y analizarlos con `pandas` (indicadores técnicos, estadísticas anualizadas, correlaciones y gráficos).

## Estructura

- [`fetch_yahoo_data.py`](fetch_yahoo_data.py) — módulo de datos:
  - `fetch_chart(symbol, range_, interval)`: llama al endpoint `query1.finance.yahoo.com/v8/finance/chart/{symbol}` y devuelve el JSON crudo.
  - `chart_to_dataframe(result)`: convierte la respuesta de Yahoo en un `DataFrame` OHLCV indexado por fecha.
  - `fetch_history(tickers, range_, interval, with_indicators=True)`: devuelve un `dict[nombre, DataFrame]` con el histórico de cada instrumento (`Retorno %` + indicadores técnicos de `indicators.py`).
  - `combine_history(histories)`: une todos los históricos en un único `DataFrame` con columnas multi-nivel (`Nombre`, `Campo`), alineado por fecha.
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
- [`visualization.py`](visualization.py) — gráficos con `matplotlib` (backend no interactivo, guarda PNG):
  - `plot_instrument(df, name)`: precio + SMA20/SMA50/EMA20 arriba, RSI14 abajo.
  - `plot_correlation_heatmap(corr)`: mapa de calor de la matriz de correlación.
  - `save_charts(histories, corr, output_dir)`: genera y guarda un PNG por instrumento + el heatmap de correlación, devuelve las rutas.
- [`main.py`](main.py) — punto de entrada: llama a `fetch_yahoo_data`, `indicators` y `visualization`, imprime resumen, histórico con indicadores, estadísticas anualizadas y correlaciones, genera los gráficos, y opcionalmente exporta datos a CSV/Excel.
  - Sin argumentos: lanza un menú interactivo (`prompt_tickers_menu` / `prompt_manual_tickers`) para elegir los índices por defecto, añadir otros manualmente, o usar solo los manuales; también pregunta si generar los gráficos.
  - Con argumentos: modo CLI vía `argparse`, pensado para scripting/automatización.
- [`app.py`](app.py) — UI web interactiva con [Streamlit](https://streamlit.io/): permite seleccionar instrumentos (por defecto y/o manuales), rango e intervalo desde la barra lateral, y muestra el resumen, las estadísticas, el heatmap de correlación y los gráficos de precio/RSI de cada instrumento directamente en el navegador.

## Uso

### UI web (Streamlit)

```bash
streamlit run app.py
```

Se abre en el navegador (`http://localhost:8501`). En la barra lateral eliges instrumentos por defecto, añades otros manuales (`Nombre=TICKER`, uno por línea), el rango/intervalo, y opcionalmente si guardar los PNGs en `charts/`. Al pulsar **Generar** se descargan los datos y se muestran el resumen, las estadísticas anualizadas, la correlación y un gráfico expandible por instrumento.

### Modo interactivo (terminal)

Si lanzas `main.py` sin argumentos, se abre un menú que pregunta si quieres usar los índices por defecto, añadir otro(s) a los de por defecto, o usar solo los que introduzcas tú (rango fijo de 6 meses):

```bash
python main.py
```

### Modo CLI (con argumentos)

```bash
# Tickers y rango por defecto (6 meses, recomendado para que SMA50/RSI tengan datos suficientes)
python main.py --range 6mo

# Cambiar rango / intervalo
python main.py --range 1y --interval 1d

# Añadir instrumentos a los de por defecto (repetible)
python main.py --ticker "Oro=GC=F"

# Usar solo instrumentos manuales, sin los de por defecto
python main.py --no-defaults --ticker "Oro=GC=F"

# Exportar el histórico combinado (con indicadores) y/o el resumen
python main.py --output out/historico.csv
python main.py --output out/historico.xlsx
python main.py --summary-output out/resumen.xlsx

# Cambiar carpeta de gráficos, o desactivarlos
python main.py --charts-dir mis_graficos
python main.py --no-charts
```

Ver `python main.py --help` para todas las opciones.

## Salida

Cada ejecución muestra por consola:

1. **Resumen** — precio actual, variación %, máx/mín 52 semanas por instrumento.
2. **Estadísticas anualizadas** — retorno anualizado, volatilidad anualizada, ratio de Sharpe y máximo drawdown por instrumento, sobre todo el rango descargado.
3. **Correlación entre retornos diarios** — matriz de correlación entre todos los instrumentos consultados (si hay más de uno).

El histórico OHLCV (con `SMA20`, `SMA50`, `EMA20`, `RSI14`, `Volatilidad %`) **no se imprime como tabla**: solo se ve en los **gráficos** — un PNG por instrumento (precio + medias móviles + RSI) y un heatmap de correlación, guardados en `charts/` por defecto — o, si usas `--output`, exportado a CSV/Excel.

## Instrumentos por defecto

| Nombre | Ticker Yahoo Finance |
|---|---|
| S&P 500 | `^GSPC` |
| MyInvestor Value Clase C | `0P0001T8V7.F` (ISIN ES0165243025) |
| DJE Gold & Ressourcen PA (EUR) Dis | `0P00000HTQ.F` (ISIN LU0159550077) |

## Requisitos

```bash
pip install pandas numpy requests openpyxl matplotlib streamlit
```

`openpyxl` solo hace falta si se exporta a `.xlsx`. `streamlit` solo hace falta para la UI web (`app.py`).
