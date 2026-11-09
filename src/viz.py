"""Shared chart style (validated palette from the dataviz reference instance).

Series colours (validated all-pairs, light mode): adoption = blue, trust = aqua, distrust = orange.
Aqua is below 3:1 contrast on the surface, so every line chart carries direct labels.
Years use an ordinal blue ramp (validated --ordinal): 2023 light -> 2025 dark.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

from src.config import FIGURES  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

ADOPTION = "#2a78d6"
TRUST = "#1baf7a"
DISTRUST = "#eb6834"
NEUTRAL_GRAY = "#b9b8b2"
YEAR_COLORS = {2023: "#86b6ef", 2024: "#2a78d6", 2025: "#104281"}


def setup() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": INK_2,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True, "lines.linewidth": 2, "legend.frameon": False,
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 22,
    })


def pct_axis(ax, axis: str = "y", lim: tuple | None = None) -> None:
    fmt = PercentFormatter(1.0, decimals=0)
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(fmt)
    if lim:
        (ax.set_ylim if axis == "y" else ax.set_xlim)(*lim)


def subtitle(ax, text: str, legend_row: bool = False) -> None:
    """Subtitle under the axes title. With legend_row=True it sits one line higher, leaving room for a
    legend placed directly above the plot (see legend_above)."""
    ax.annotate(text, xy=(0, 1), xycoords="axes fraction", xytext=(0, 24 if legend_row else 6),
                textcoords="offset points", fontsize=9, color=INK_2, va="bottom")
    if legend_row:
        ax.set_title(ax.get_title(loc="left"), loc="left", pad=42)


def legend_above(ax, **kw) -> None:
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.0), ncol=kw.pop("ncol", 3), fontsize=9,
              handletextpad=0.3, borderaxespad=0.2, **kw)


def footnote(fig, text: str) -> None:
    """Source/base note placed just below everything already drawn (call after tight_layout)."""
    fig.canvas.draw()
    bb = fig.get_tightbbox(fig.canvas.get_renderer())
    y = bb.y0 / fig.get_figheight() - 0.015
    fig.text(0.01, y, text, fontsize=7.5, color=MUTED, va="top", ha="left", wrap=True)


def repel_labels(ax, xs, ys, texts, min_dy: float, x_span: float, dx: float = 0.0, **kw) -> None:
    """Greedy vertical de-collision for direct labels (data units). Labels that move get a hairline leader."""
    placed = []
    for x, y, t in sorted(zip(xs, ys, texts), key=lambda r: -r[1]):
        ly = y
        while any(abs(px - x) < x_span and abs(py - ly) < min_dy for px, py in placed):
            ly -= min_dy / 3
        placed.append((x, ly))
        arrow = dict(arrowstyle="-", color=AXIS, lw=0.6) if abs(ly - y) > min_dy / 2 else None
        ax.annotate(t, (x, y), xytext=(x + dx, ly), textcoords="data", va="center", fontsize=kw.get("fontsize", 8),
                    color=kw.get("color", INK_2), arrowprops=arrow)


def save(fig, name: str) -> str:
    path = FIGURES / f"{name}.png"
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    return str(path)
