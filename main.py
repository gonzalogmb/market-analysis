"""Punto de entrada: lee datos de mercado desde Yahoo Finance y los muestra/exporta con pandas."""

import argparse
from pathlib import Path

import pandas as pd

from fetch_yahoo_data import TICKERS, combine_history, fetch_history, fetch_summary


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
        help="Instrumento a consultar, ej. --ticker \"S&P 500=^GSPC\". Repetible. Si se omite, usa el set por defecto.",
    )
    parser.add_argument("--range", dest="range_", default="1mo", help="Rango histórico (5d, 1mo, 3mo, 1y, ...). Default: 1mo")
    parser.add_argument("--interval", default="1d", help="Intervalo de velas (1d, 1wk, 1mo, ...). Default: 1d")
    parser.add_argument("--output", type=Path, help="Ruta de salida para el histórico combinado (.csv o .xlsx)")
    parser.add_argument("--summary-output", type=Path, help="Ruta de salida para el resumen (.csv o .xlsx)")
    return parser.parse_args()


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".xlsx":
        df.to_excel(path)
    else:
        df.to_csv(path)
    print(f"Guardado en {path}")


def main() -> None:
    args = parse_args()
    tickers = parse_tickers(args.tickers) if args.tickers else TICKERS

    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", None)

    summary = fetch_summary(tickers)
    print("=== Resumen ===")
    print(summary)
    if args.summary_output:
        save_dataframe(summary, args.summary_output)

    histories = fetch_history(tickers, range_=args.range_, interval=args.interval)
    combined = combine_history(histories)
    print(f"\n=== Histórico combinado ({args.range_}) ===")
    print(combined)
    if args.output:
        save_dataframe(combined, args.output)


if __name__ == "__main__":
    main()
