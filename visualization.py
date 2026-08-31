"""Gráficos de precio, indicadores técnicos y correlaciones, guardados como PNG con matplotlib."""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


MAX_TITLE_LEN = 15


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower())
    return slug.strip("_") or "instrumento"


def _truncate(name: str, max_len: int = MAX_TITLE_LEN) -> str:
    return name if len(name) <= max_len else name[: max_len - 1] + "…"


def plot_instrument(df: pd.DataFrame, name: str) -> plt.Figure:
    """Precio + SMA20/SMA50/EMA20 arriba, RSI14 y volatilidad móvil abajo."""
    fig, (ax_price, ax_rsi) = plt.subplots(
        2, 1, figsize=(6, 4), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )

    ax_price.plot(df.index, df["Close"], label="Close", color="black", linewidth=1.2)
    for col, style in (("SMA20", "--"), ("SMA50", "--"), ("EMA20", ":")):
        if col in df.columns:
            ax_price.plot(df.index, df[col], style, label=col, linewidth=1)
    ax_price.set_title(_truncate(name))
    ax_price.set_ylabel("Precio")
    ax_price.legend(loc="upper left", fontsize=8)
    ax_price.grid(alpha=0.3)

    if "RSI14" in df.columns:
        ax_rsi.plot(df.index, df["RSI14"], color="tab:purple", linewidth=1)
        ax_rsi.axhline(70, color="red", linestyle="--", linewidth=0.8)
        ax_rsi.axhline(30, color="green", linestyle="--", linewidth=0.8)
        ax_rsi.set_ylim(0, 100)
        ax_rsi.set_ylabel("RSI14")
        ax_rsi.grid(alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def plot_correlation_heatmap(corr: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(0.9 * len(corr.columns) + 1.5, 0.9 * len(corr.columns) + 0.8))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="RdYlGn")

    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels([_truncate(c) for c in corr.columns], rotation=45, ha="right", fontsize=6)
    ax.set_yticks(range(len(corr.index)))
    ax.set_yticklabels([_truncate(i) for i in corr.index], fontsize=6)

    for i in range(len(corr.index)):
        for j in range(len(corr.columns)):
            ax.text(j, i, f"{corr.iat[i, j]:.2f}", ha="center", va="center", fontsize=6)

    ax.set_title("Correlación entre retornos diarios", fontsize=9)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def save_charts(
    histories: dict[str, pd.DataFrame], corr: pd.DataFrame | None, output_dir: Path
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for name, df in histories.items():
        fig = plot_instrument(df, name)
        path = output_dir / f"{_slugify(name)}.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        saved.append(path)

    if corr is not None and len(corr.columns) > 1:
        fig = plot_correlation_heatmap(corr)
        path = output_dir / "correlacion.png"
        fig.savefig(path, dpi=120)
        plt.close(fig)
        saved.append(path)

    return saved
