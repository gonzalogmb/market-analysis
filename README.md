# market-analysis

Herramienta en Python para consultar datos de mercado (índices y fondos de inversión) directamente desde la API pública de Yahoo Finance, sin depender de la librería `yfinance`, y analizarlos con `pandas` (indicadores técnicos, estadísticas anualizadas y correlaciones).

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
- [`main.py`](main.py) — punto de entrada: llama a `fetch_yahoo_data` e `indicators`, imprime resumen, histórico con indicadores, estadísticas anualizadas y correlaciones, y opcionalmente exporta a CSV/Excel.
  - Sin argumentos: lanza un menú interactivo (`prompt_tickers_menu` / `prompt_manual_tickers`) para elegir los índices por defecto, añadir otros manualmente, o usar solo los manuales.
  - Con argumentos: modo CLI vía `argparse`, pensado para scripting/automatización.

## Uso

### Modo interactivo

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
```

Ver `python main.py --help` para todas las opciones.

## Salida

Cada ejecución muestra:

1. **Resumen** — precio actual, variación %, máx/mín 52 semanas por instrumento.
2. **Histórico combinado** — OHLCV + `Retorno %`, `SMA20`, `SMA50`, `EMA20`, `RSI14`, `Volatilidad %` por instrumento y fecha.
3. **Estadísticas anualizadas** — retorno anualizado, volatilidad anualizada, ratio de Sharpe y máximo drawdown por instrumento, sobre todo el rango descargado.
4. **Correlación entre retornos diarios** — matriz de correlación entre todos los instrumentos consultados (si hay más de uno).

## Instrumentos por defecto

| Nombre | Ticker Yahoo Finance |
|---|---|
| S&P 500 | `^GSPC` |
| MyInvestor Value Clase C | `0P0001T8V7.F` (ISIN ES0165243025) |
| DJE Gold & Ressourcen PA (EUR) Dis | `0P00000HTQ.F` (ISIN LU0159550077) |

## Requisitos

```bash
pip install pandas numpy requests openpyxl
```

`openpyxl` solo hace falta si se exporta a `.xlsx`.
