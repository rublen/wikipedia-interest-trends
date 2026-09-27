"""One-page A4 PDF report: what was measured, chart, table, ranking, recommendation, limits."""

from __future__ import annotations

import logging
import textwrap
from datetime import date
from functools import lru_cache
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.ft2font import FT2Font  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from wikitrends import __version__, chart, trust  # noqa: E402

# Fallback fonts often lack a bold face; matplotlib then logs a warning per text item.
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

A4 = (8.27, 11.69)
LEFT = 0.07
WRAP = 108            # characters per line for 8.5pt body text across the page
LINE = 0.0128         # line height (figure fraction) for body text
# Bundled DejaVu Sans covers Latin, Greek and Cyrillic; the others are tried in order for
# other scripts (CJK, Devanagari, Arabic...) when installed.
FALLBACK_FONTS = ["DejaVu Sans", "Noto Sans CJK JP", "Noto Sans CJK SC", "Hiragino Sans",
                  "Arial Unicode MS", "Noto Sans"]


@lru_cache(maxsize=1)
def _font_chain() -> tuple[tuple[str, str], ...]:
    """(family, file) for each installed fallback font, in order."""
    installed = {f.name: f.fname for f in font_manager.fontManager.ttflist}
    return tuple((name, installed[name]) for name in FALLBACK_FONTS if name in installed)


@lru_cache(maxsize=None)
def _has_glyph(path: str, char: str) -> bool:
    return FT2Font(path).get_char_index(ord(char)) != 0


def renderable(text: str) -> bool:
    """True if every character can be drawn by some installed font in the chain."""
    fonts = [path for _, path in _font_chain()]
    return all(c.isspace() or any(_has_glyph(p, c) for p in fonts) for c in text)


def _safe(text: str | None, fallback: str) -> str:
    return text if text and renderable(text) else fallback


class _Page:
    """Top-down text cursor on a figure (coordinates are figure fractions)."""

    def __init__(self, fig):
        self.fig = fig
        self.y = 0.955

    def text(self, s: str, size: float = 8.5, color: str = chart.TEXT_PRIMARY, weight: str = "normal",
             wrap: int = WRAP, gap: float = 0.0, x: float = LEFT) -> None:
        lines = textwrap.wrap(s, wrap) or [""]
        for line in lines:
            self.fig.text(x, self.y, line, fontsize=size, color=color, weight=weight, va="top")
            self.y -= LINE * size / 8.5
        self.y -= gap

    def heading(self, s: str) -> None:
        self.y -= 0.006
        self.text(s, size=10.5, weight="bold", gap=0.003)


def render(path: Path, result: dict, months: list[str], plotted: dict[str, dict],
           compared: tuple[list[str], list[str]], order: list[str], lang_names: dict[str, str],
           question: str | None, note: str | None, command: str) -> bool:
    """Write the PDF. Returns False if the content didn't fit on one page."""
    families = [name for name, _ in _font_chain()] or ["DejaVu Sans"]
    with plt.rc_context({"font.family": families}):
        return _render(path, result, months, plotted, compared, order, lang_names, question, note, command)


def _render(path, result, months, plotted, compared, order, lang_names, question, note, command) -> bool:
    fig = plt.figure(figsize=A4, facecolor=chart.SURFACE)
    page = _Page(fig)
    topic = result["topic"]
    ranking = result["ranking"]
    # Many languages: keep one page by showing the first reason only (reasons that lowered
    # the confidence come first) and a shorter chart.
    compact = len(ranking["languages"]) + len(ranking["not_ranked"]) > 5

    def name(lang: str) -> str:
        return f"{lang_names.get(lang, lang)} ({lang})"

    # Header.
    page.text(f"Wikipedia interest report · {date.today().isoformat()}", size=8, color=chart.TEXT_SECONDARY)
    page.text(question or f"Interest in “{topic['label']}” across Wikipedia language editions",
              size=15, weight="bold", wrap=58, gap=0.004)

    # What was measured.
    page.heading("What was measured")
    page.text(f"Wikidata item {topic['qid']}: “{topic['label']}” ({topic['description']}).")
    if note:
        page.text(note)
    page.text(f"Compared: {result['period']['comparison']} ({result['period']['recent']} vs "
              f"{result['period']['previous']}). Main measure: the article's share of all views in its "
              "Wikipedia, so languages of different size and traffic trends are comparable.")

    # Chart: share per million, the comparable measure.
    langs = [lang for lang in order if lang in plotted][:chart.MAX_SERIES]
    colors = chart.assign_colors(order)
    chart_height = 0.14 if compact else 0.17
    ax = fig.add_axes((LEFT + 0.02, page.y - chart_height - 0.02, 0.8, chart_height))
    if langs:
        spans = chart.compared_spans(months, compared)
        ends = chart.draw_panel(ax, months, plotted, "share", langs, colors, spans)
        ax.set_ylim(bottom=0, top=max(ax.get_ylim()[1], 1e-3))
        step = max(1, len(months) // 8)
        ax.set_xticks(list(range(len(months)))[::step], months[::step])
        ax.set_title("Share of all views in that Wikipedia, per million (shaded: compared months)",
                     loc="left", fontsize=8.5, color=chart.TEXT_SECONDARY)
        if len(langs) > 1:
            ax.legend([Line2D([], [], color=colors[lang], linewidth=1.8) for lang in langs], langs,
                      loc="upper left", bbox_to_anchor=(1.01, 1.0), frameon=False, fontsize=8)
        if len(langs) <= chart.MAX_DIRECT_LABELS:  # more labels than this collide; the legend names them
            chart.direct_labels(fig, ax, len(months) - 1, ends)
    else:
        ax.axis("off")
        ax.text(0, 0.5, "No language has an article to chart.", fontsize=9, color=chart.TEXT_SECONDARY)
    page.y -= chart_height + 0.055

    # Table.
    page.heading("Results by language (best-ranked first)")
    columns = [("Rank", 0.0), ("Language", 0.045), ("Article", 0.195), ("Views/mo", 0.405),
               ("Share", 0.485), ("Verdict", 0.585), ("Confidence", 0.73), ("Score", 0.83)]
    for label, dx in columns:
        fig.text(LEFT + dx, page.y, label, fontsize=8, weight="bold", color=chart.TEXT_SECONDARY, va="top")
    page.y -= LINE * 1.2
    languages = result["languages"]
    for row in ranking["languages"]:
        lang = row["lang"]
        title = _safe(languages[lang].get("title"), "(title in a script without an installed font)")
        change = row["share_growth_pct"]
        cells = [str(row["rank"]), name(lang), textwrap.shorten(title, 30, placeholder="…"),
                 f"{row['avg_monthly_views']:,}", f"{'rose' if change > 0 else 'fell'} {abs(change):.1f}%",
                 row["verdict"].replace("_", " "), row["confidence"],
                 f"{row['score']:.2f}" if len(ranking["languages"]) > 1 else "–"]  # 1 language: no ranking
        for (label, dx), cell in zip(columns, cells):
            fig.text(LEFT + dx, page.y, cell, fontsize=8, color=chart.TEXT_PRIMARY, va="top")
        page.y -= LINE * 1.1
    for lang, reason in ranking["not_ranked"].items():
        fig.text(LEFT + columns[1][1], page.y, name(lang), fontsize=8, color=chart.TEXT_SECONDARY, va="top")
        fig.text(LEFT + columns[2][1], page.y, textwrap.shorten(reason, 95, placeholder="…"),
                 fontsize=8, color=chart.TEXT_SECONDARY, va="top")
        page.y -= LINE * 1.1

    # Recommendation, written by code from the ranking.
    page.heading("Audiences to explore next")
    for line in result["recommendation"]:
        page.text("• " + line, gap=0.002)

    # Trust: the meaning of each level once, then each language's main reasons.
    page.heading("How far to trust each result")
    page.text("Confidence: " + "; ".join(f"{level} = {meaning}" for level, meaning in
                                          trust.MEANINGS.items()) + ".",
              color=chart.TEXT_SECONDARY, gap=0.002)
    for row in ranking["languages"]:
        trend = languages[row["lang"]]["trend"]
        reasons = "; ".join(trend["reasons"][:1 if compact else 2])
        page.text(f"{name(row['lang'])} ({trend['confidence']}): {reasons[:1].upper()}{reasons[1:]}.",
                  gap=0.001)

    # Method and limits.
    page.heading("How the ranking works, and its limits")
    w = ranking["weights"]
    page.text(f"Score = {w['momentum']:g} × momentum (change in share) + {w['size']:g} × size (average "
              f"monthly views, log scale) + {w['confidence']:g} × confidence (high 1, medium 0.5, low 0). "
              "Each part is scaled 0–1 within the compared languages, so the score ranks only this group. "
              "Weights can be changed (--weights).", gap=0.002)
    page.text(result["scope"], gap=0.002)
    for limitation in result["limitations"][1:2 if compact else 3]:
        page.text(limitation, gap=0.002)

    fig.text(LEFT, 0.028, f"Source: Wikimedia Pageviews API (monthly, agent=user) and Wikidata. "
             f"wikipedia-interest-trends {__version__}.", fontsize=6.5, color=chart.TEXT_SECONDARY)
    fig.text(LEFT, 0.016, textwrap.shorten(f"Reproduce: {command}", 150, placeholder="…"),
             fontsize=6.5, color=chart.TEXT_SECONDARY)
    fits = page.y >= 0.045  # the footer starts below this

    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(path) as pdf:
        pdf.savefig(fig, facecolor=chart.SURFACE)
    plt.close(fig)
    return fits
