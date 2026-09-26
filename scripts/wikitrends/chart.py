"""Two-panel PNG: normalized share (comparable across languages) and raw monthly views."""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

# Validated categorical palette, fixed order (never cycled).
SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
MAX_SERIES = len(SERIES_COLORS)
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
COMPARED_FILL = "#efeee9"  # recessive band behind the two compared periods
LOG_SCALE_RATIO = 20  # raw views use a log axis when languages differ this much in size
MAX_DIRECT_LABELS = 4
DPI = 150
LABEL_FONT_PT = 9
LABEL_GAP_PX = LABEL_FONT_PT * 1.25 * DPI / 72  # minimum vertical distance between direct labels


def assign_colors(order: list[str]) -> dict[str, str]:
    """Color by position among the *requested* languages, so colors don't shift when one is missing."""
    return {lang: SERIES_COLORS[i] for i, lang in enumerate(order[:MAX_SERIES])}


def render(
    path: Path,
    title: str,
    months: list[str],
    series: dict[str, dict],
    footnote: str,
    order: list[str] | None = None,
    not_shown: dict[str, str] | None = None,
    compared: tuple[list[str], list[str]] | None = None,
) -> list[str]:
    """series: {lang: {"views": {month: int}, "share": {month: float|None}}}.

    order: all requested languages; colors follow this order so a language keeps its
      color when another one has no data.
    not_shown: {lang: reason} for requested languages without a line (e.g. no article);
      listed in the legend so they don't silently disappear.
    compared: (year-earlier months, recent months) to shade; default: the two halves.
    Returns the languages that were plotted.
    """
    order = order or list(series)
    not_shown = dict(not_shown or {})
    colors = assign_colors(order)
    langs = [lang for lang in order if lang in series and lang in colors]
    for lang in series:
        if lang not in colors:
            not_shown[lang] = f"not drawn (max {MAX_SERIES} lines)"
    x = list(range(len(months)))
    if compared is None:
        half = len(months) // 2
        compared = (months[:half], months[half:])
    spans = [(months.index(period[0]) - 0.5, months.index(period[-1]) + 0.5) for period in compared]

    fig, (ax_share, ax_views) = plt.subplots(2, 1, figsize=(9, 6.4), sharex=True, facecolor=SURFACE)
    fig.suptitle(title, x=0.06, y=0.975, ha="left", fontsize=13, fontweight="bold", color=TEXT_PRIMARY)

    # Decide the scale first: zeros are real data and are drawn, except on a log axis.
    positive = [v for lang in langs for v in series[lang]["views"].values() if v > 0]
    log_scale = bool(positive) and max(positive) / min(positive) >= LOG_SCALE_RATIO

    line_ends: dict = {ax_share: [], ax_views: []}
    for ax, key in [(ax_share, "share"), (ax_views, "views")]:
        ax.set_facecolor(SURFACE)
        drop_zeros = key == "views" and log_scale
        for lang in langs:
            values = series[lang][key]
            y = [values.get(m) for m in months]
            y = [math.nan if v is None or (drop_zeros and v <= 0) else v for v in y]
            ax.plot(x, y, color=colors[lang], linewidth=1.8, label=lang, solid_capstyle="round")
            last = next((v for v in reversed(y) if not math.isnan(v)), None)
            if last is not None:
                line_ends[ax].append((lang, last))
        for left, right in spans:
            ax.axvspan(left, right, color=COMPARED_FILL, zorder=0, linewidth=0)
        # The two periods touch when 12 months are compared; mark where the recent one starts.
        ax.axvline(spans[1][0], color=TEXT_SECONDARY, linewidth=0.8, linestyle=(0, (4, 3)), zorder=1)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.tick_params(colors=TEXT_SECONDARY, labelsize=8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)

    ax_share.set_title("Share of all views in that Wikipedia (per million)", loc="left",
                       fontsize=10, color=TEXT_SECONDARY)
    ax_share.set_ylim(bottom=0)
    if log_scale:
        ax_views.set_yscale("log")
    else:
        ax_views.set_ylim(bottom=0, top=max(1, ax_views.get_ylim()[1]))
    ax_views.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax_views.yaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))
    ax_views.set_title("Monthly article views (agent = user" + (", log scale)" if log_scale else ")"),
                       loc="left", fontsize=10, color=TEXT_SECONDARY)
    ax_share.set_ylim(top=max(ax_share.get_ylim()[1], 1e-3))

    ymax = ax_share.get_ylim()[1]
    for text, (left, _) in zip(("year earlier", "compared months"), spans):
        ax_share.text(left + 0.3, ymax * 0.97, text, ha="left", va="top", fontsize=8, color=TEXT_SECONDARY)

    step = max(1, len(months) // 8)
    ax_views.set_xticks(x[::step], months[::step])
    handles, labels = ax_share.get_legend_handles_labels()
    for lang, reason in not_shown.items():  # requested but without a line: say why
        handles.append(Line2D([], [], linestyle="none"))
        labels.append(f"{lang} — {reason}")
    has_legend = len(handles) > 1  # a single series is named by the title; no legend box
    if has_legend:
        legend = fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.06, 0.935),
                            ncol=min(len(handles), 5), frameon=False, fontsize=9, handlelength=1.6)
        for text in legend.get_texts()[len(langs):]:
            text.set_color(TEXT_SECONDARY)
        for text in legend.get_texts()[:len(langs)]:
            text.set_color(TEXT_PRIMARY)
    fig.text(0.06, 0.015, footnote, fontsize=7.5, color=TEXT_SECONDARY, ha="left")
    fig.tight_layout(rect=(0.02, 0.04, 0.95, 0.915 if has_legend else 0.95))

    if len(langs) <= MAX_DIRECT_LABELS:
        for ax, ends in line_ends.items():
            _direct_labels(fig, ax, x[-1], ends)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=SURFACE)
    plt.close(fig)
    return langs


def _direct_labels(fig, ax, x_end: float, ends: list[tuple[str, float]]) -> None:
    """Label each line at its right end, nudging labels apart so they never overlap."""
    if not ends:  # e.g. an article with no views at all in the period
        return
    fig.set_dpi(DPI)  # positions below are in output pixels
    points = sorted(((lang, y, ax.transData.transform((x_end, y))[1]) for lang, y in ends),
                    key=lambda p: p[2])
    placed: list[float] = []
    for _, _, y_px in points:
        placed.append(max(y_px, placed[-1] + LABEL_GAP_PX) if placed else y_px)
    # Pushing only upward biases the stack; re-centre it on the original positions.
    shift = (sum(placed) - sum(p[2] for p in points)) / len(points)
    shift = min(shift, placed[0] - ax.get_window_extent().y0)  # keep the stack inside the panel
    for (lang, y, y_px), target in zip(points, placed):
        ax.annotate(lang, (x_end, y), xytext=(6, (target - shift - y_px) * 72 / DPI),
                    textcoords="offset points", va="center", fontsize=LABEL_FONT_PT, color=TEXT_PRIMARY,
                    annotation_clip=False)
