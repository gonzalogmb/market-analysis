"""Punto de entrada: lee datos de mercado desde Yahoo Finance y los muestra/exporta con pandas."""

import argparse
import sys
from pathlib import Path

import pandas as pd

from fetch_yahoo_data import TICKERS, combine_history, fetch_history, fetch_summary
from indicators import correlation_matrix, stats_summary
from visualization import save_charts


def parse_tickers(pairs: list[str]) -> dict[str, str]:
    tickers = {}
    for pair in pairs:
        name, _, symbol = pair.partition("=")
        if not symbol:
            raise argparse.ArgumentTypeError(f"Formato inválido '{pair}', usa Nombre=TICKER")
        tickers[name] = symbol
    return tickers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Descarga datos de Yahoo Finance y los exporta con pandas.")
    parser.add_argument(
        "--ticker",
        dest="tickers",
        action="append",
        metavar="Nombre=TICKER",
        help="Instrumento adicional a consultar, ej. --ticker \"Oro=GC=F\". Repetible. Se suma a los tickers por defecto (si el nombre coincide con uno existente, lo sobreescribe).",
    )
    parser.add_argument(
        "--no-defaults",
        action="store_true",
        help="No incluir los tickers por defecto, usar solo los pasados con --ticker.",
    )
    parser.add_argument(
        "--range",
        dest="range_",
        default="6mo",
        help="Rango histórico (5d, 1mo, 3mo, 6mo, 1y, ...). Default: 6mo (recomendado para que SMA50/RSI tengan datos suficientes)",
    )
    parser.add_argument("--interval", default="1d", help="Intervalo de velas (1d, 1wk, 1mo, ...). Default: 1d")
    parser.add_argument("--output", type=Path, help="Ruta de salida para el histórico combinado (.csv o .xlsx)")
    parser.add_argument("--summary-output", type=Path, help="Ruta de salida para el resumen (.csv o .xlsx)")
    parser.add_argument(
        "--charts-dir", type=Path, default=Path("charts"), help="Carpeta donde guardar los gráficos PNG. Default: charts/"
    )
    parser.add_argument("--no-charts", action="store_true", help="No generar gráficos.")
    return parser.parse_args()


def prompt_manual_tickers() -> dict[str, str]:
    print("Introduce Nombre y Ticker de Yahoo Finance (deja el nombre vacío para terminar).")
    manual = {}
    while True:
        name = input("Nombre: ").strip()
        if not name:
            break
        symbol = input("Ticker: ").strip()
        if not symbol:
            print("Ticker vacío, se ignora.")
            continue
        manual[name] = symbol
    return manual


def prompt_tickers_menu() -> dict[str, str]:
    print("Instrumentos por defecto:")
    for name, symbol in TICKERS.items():
        print(f"  - {name} ({symbol})")

    print("\n¿Qué quieres consultar?")
    print("  1) Los índices por defecto")
    print("  2) Los de por defecto + otro(s) que introduzca yo")
    print("  3) Solo el/los que introduzca yo")

    choice = input("Elige una opción [1]: ").strip() or "1"

    if choice == "2":
        return {**TICKERS, **prompt_manual_tickers()}
    if choice == "3":
        manual = prompt_manual_tickers()
        return manual or dict(TICKERS)

    return dict(TICKERS)


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".xlsx":
        df.to_excel(path)
    else:
        df.to_csv(path)
    print(f"Guardado en {path}")


def main() -> None:
    if len(sys.argv) == 1:
        tickers = prompt_tickers_menu()
        range_, interval = "6mo", "1d"
        output = summary_output = None
        want_charts = (input("\n¿Generar gráficos en charts/? [S/n]: ").strip().lower() or "s") == "s"
        charts_dir = Path("charts")
    else:
        args = parse_args()
        base = {} if args.no_defaults else TICKERS
        tickers = {**base, **parse_tickers(args.tickers or [])}
        if not tickers:
            raise SystemExit("No hay tickers para consultar: usa --ticker o quita --no-defaults.")
        range_, interval = args.range_, args.interval
        output, summary_output = args.output, args.summary_output
        want_charts = not args.no_charts
        charts_dir = args.charts_dir

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    summary = fetch_summary(tickers)
    print("\n=== Resumen ===")
    print(summary)
    if summary_output:
        save_dataframe(summary, summary_output)

    histories = fetch_history(tickers, range_=range_, interval=interval)
    if output:
        combined = combine_history(histories)
        save_dataframe(combined, output)

    print("\n=== Estadísticas anualizadas ===")
    print(stats_summary(histories))

    corr = None
    if len(histories) > 1:
        corr = correlation_matrix(histories)
        print("\n=== Correlación entre retornos diarios ===")
        print(corr.round(2))

    if want_charts:
        saved = save_charts(histories, corr, charts_dir)
        print(f"\n=== Gráficos guardados en {charts_dir}/ ===")
        for path in saved:
            print(f"  - {path}")


if __name__ == "__main__":
    main()
