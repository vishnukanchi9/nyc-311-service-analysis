"""Chart functions for the NYC 311 analysis. Each takes a query-result DataFrame
and returns a matplotlib Figure; `save()` writes it to images/."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm

IMG_DIR = Path(__file__).resolve().parents[1] / "images"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"      # primary series / "faster than expected"
ORANGE = "#eb6834"    # second series / "slower than expected"
NEUTRAL = "#c9c8c2"   # diverging midpoint

SEQ = LinearSegmentedColormap.from_list("seq_blue", ["#eef4fc", "#9cc3ef", BLUE, "#123f7a"])
DIV = LinearSegmentedColormap.from_list("div", [ORANGE, "#f6c7b2", "#f1f0ec", "#b6d2f3", BLUE])

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 10,
    "text.color": INK,
    "axes.labelcolor": INK_2,
    "axes.edgecolor": GRID,
    "axes.titlesize": 13,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.titlepad": 24,
    "axes.axisbelow": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "xtick.major.size": 0,
    "ytick.major.size": 0,
    "legend.frameon": False,
})


def _subtitle(ax, text: str) -> None:
    ax.text(0, 1.015, text, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")


def _source(fig, text: str = "Source: NYC Open Data, 311 Service Requests (2025)") -> None:
    fig.text(0.01, 0.005, text, color=INK_2, fontsize=8, ha="left", va="bottom")


def save(fig, name: str) -> Path:
    IMG_DIR.mkdir(exist_ok=True)
    path = IMG_DIR / f"{name}.png"
    fig.savefig(path, dpi=160, bbox_inches="tight")
    return path


def monthly_volume(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 4))
    x = pd.to_datetime(df["month"])
    ax.plot(x, df["requests"] / 1000, color=BLUE, lw=2, marker="o", ms=5)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}K"))
    ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%b"))
    ax.grid(axis="x", visible=False)
    peak = df.loc[df["requests"].idxmax()]
    ax.annotate(f"{pd.to_datetime(peak['month']):%B}: {peak['requests'] / 1000:,.0f}K",
                (pd.to_datetime(peak["month"]), peak["requests"] / 1000),
                xytext=(0, 10), textcoords="offset points", ha="center", color=INK, fontsize=9)
    ax.set_title("311 requests per month, 2025")
    _subtitle(ax, "Thousands of service requests created")
    _source(fig)
    return fig


def top_complaints(df: pd.DataFrame, n: int = 12):
    d = df.head(n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 5.2))
    ax.barh(d["complaint_group"], d["requests"] / 1000, color=BLUE, height=0.7)
    for y, (v, p) in enumerate(zip(d["requests"], d["pct_of_total"])):
        ax.text(v / 1000, y, f"  {v / 1000:,.0f}K ({p:.1f}%)", va="center", fontsize=8.5, color=INK_2)
    ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}K"))
    ax.set_xlim(0, d["requests"].max() / 1000 * 1.22)
    top3 = df["cumulative_pct"].iloc[2]
    ax.set_title("Top complaint types")
    _subtitle(ax, f"The top 3 types alone account for {top3:.0f}% of all requests")
    _source(fig)
    return fig


def seasonality_heatmap(df: pd.DataFrame):
    pivot = df.pivot(index="complaint_group", columns="month_num", values="seasonal_index")
    pivot = pivot.loc[pivot.max(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(10, 4.6))
    vmax = pivot.values.max()
    norm = TwoSlopeNorm(vcenter=100, vmin=0, vmax=vmax)
    # reversed diverging map: above-average months are orange (busy), below are blue
    im = ax.imshow(pivot.values, cmap=DIV.reversed(), norm=norm, aspect="auto")
    ax.set_xticks(range(12), ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    ax.set_yticks(range(len(pivot)), pivot.index)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7.5,
                    color="white" if v > 100 + (vmax - 100) * 0.6 else INK)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=INK_2)
    ax.set_title("Seasonality of the eight biggest complaint types")
    _subtitle(ax, "Monthly volume indexed to each type's own average month (100 = average)")
    _source(fig)
    return fig


def hour_weekday_heatmap(df: pd.DataFrame):
    order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = df.pivot(index="weekday", columns="hour", values="requests").loc[order]
    fig, ax = plt.subplots(figsize=(11, 3.8))
    im = ax.imshow(pivot.values / 1000, cmap=SEQ, aspect="auto")
    ax.set_xticks(range(0, 24, 2), [f"{h:02d}:00" for h in range(0, 24, 2)])
    ax.set_yticks(range(7), [d[:3] for d in order])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cb.set_label("Thousand requests", color=INK_2, fontsize=8)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8, colors=INK_2)
    ax.set_title("When New Yorkers file 311 requests")
    _subtitle(ax, "Requests by hour of day and day of week (midnight back-office timestamps excluded)")
    _source(fig)
    return fig


def agency_resolution(df: pd.DataFrame):
    d = df.sort_values("median_hours")
    fig, ax = plt.subplots(figsize=(9, 5))
    y = np.arange(len(d))
    ax.hlines(y, d["median_hours"], d["p90_hours"], color=GRID, lw=2.5, zorder=1)
    ax.scatter(d["median_hours"], y, color=BLUE, s=60, zorder=3, label="Median",
               edgecolors=SURFACE, linewidths=2)
    ax.scatter(d["p90_hours"], y, color=ORANGE, s=60, zorder=3, label="90th percentile",
               edgecolors=SURFACE, linewidths=2)
    ax.set_xscale("log")
    ticks = [1, 4, 24, 24 * 7, 24 * 30, 24 * 180]
    ax.set_xticks(ticks, ["1 hr", "4 hrs", "1 day", "1 week", "1 month", "6 months"])
    ax.xaxis.set_minor_locator(mticker.NullLocator())
    ax.set_yticks(y, [f"{a}  ({n / 1000:,.0f}K)" for a, n in zip(d["agency"], d["requests"])])
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title("Time to close a request, by agency")
    _subtitle(ax, "Median and 90th-percentile resolution time (log scale); request volume in brackets")
    _source(fig)
    return fig


def borough_raw_vs_adjusted(df: pd.DataFrame):
    d = df.sort_values("pct_faster_than_citywide")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
    ax1.barh(d["borough"].str.title(), d["raw_median_hours"], color=NEUTRAL, height=0.65)
    for y, v in enumerate(d["raw_median_hours"]):
        ax1.text(v, y, f"  {v:.1f} h", va="center", fontsize=9, color=INK_2)
    ax1.set_xlim(0, d["raw_median_hours"].max() * 1.25)
    ax1.set_title("Raw median hours to close", fontsize=11, pad=8)
    ax1.grid(axis="y", visible=False)

    colors = [ORANGE if v < 50 else BLUE for v in d["pct_faster_than_citywide"]]
    ax2.barh(d["borough"].str.title(), d["pct_faster_than_citywide"] - 50, left=50,
             color=colors, height=0.65)
    ax2.axvline(50, color=INK_2, lw=1)
    for y, v in enumerate(d["pct_faster_than_citywide"]):
        ax2.text(v + (0.3 if v >= 50 else -0.3), y, f"{v:.1f}%", va="center",
                 ha="left" if v >= 50 else "right", fontsize=9, color=INK)
    span = max(abs(d["pct_faster_than_citywide"] - 50)) + 3
    ax2.set_xlim(50 - span, 50 + span)
    ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.set_title("Mix-adjusted: % closed faster than citywide norm", fontsize=11, pad=8)
    ax2.grid(axis="y", visible=False)
    fig.suptitle("Raw averages hide which boroughs are really slower", x=0.01, ha="left",
                 fontsize=13, fontweight="semibold")
    fig.text(0.01, 0.885, "Right: each request compared with the citywide median for its complaint "
             "type. 50% = exactly as fast as the city norm.", color=INK_2, fontsize=9.5)
    fig.subplots_adjust(top=0.74, wspace=0.08)
    _source(fig)
    return fig


def district_ranking(df: pd.DataFrame, n: int = 10):
    d = pd.concat([df.head(n), df.tail(n)]).sort_values("share_faster")
    d = d.drop_duplicates("community_board")
    pct = d["share_faster"] * 100
    fig, ax = plt.subplots(figsize=(9, 7))
    labels = [cb.split(" ", 1)[1].title() + " CD " + cb.split(" ", 1)[0] for cb in d["community_board"]]
    colors = [ORANGE if v < 50 else BLUE for v in pct]
    ax.barh(labels, pct - 50, left=50, color=colors, height=0.7)
    ax.axvline(50, color=INK_2, lw=1)
    for y, v in enumerate(pct):
        ax.text(v + (0.4 if v >= 50 else -0.4), y, f"{v:.0f}%", va="center",
                ha="left" if v >= 50 else "right", fontsize=8.5, color=INK)
    ax.axhline(n - 0.5, color=GRID, lw=1, ls="--")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", visible=False)
    ax.set_title(f"The {n} slowest and {n} fastest community districts")
    _subtitle(ax, "% of requests closed faster than the citywide median for the same complaint type")
    _source(fig)
    return fig


def nypd_core_types(df: pd.DataFrame):
    """Small multiples: median NYPD response by borough for its three biggest types."""
    types = ["Noise - Residential", "Illegal Parking", "Blocked Driveway"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharex=True)
    for ax, t in zip(axes, types):
        d = df[df["complaint_group"] == t].sort_values("median_hours")
        colors = [ORANGE if b == "BRONX" else NEUTRAL for b in d["borough"]]
        ax.barh(d["borough"].str.title(), d["median_hours"], color=colors, height=0.65)
        for y, (v, pct) in enumerate(zip(d["median_hours"], d["pct_of_citywide"])):
            ax.text(v, y, f"  {v:.1f} h", va="center", fontsize=8.5, color=INK_2)
        ax.set_title(t, fontsize=11, pad=8)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, df["median_hours"].max() * 1.3)
    fig.suptitle("NYPD takes up to twice as long to close the same complaint in the Bronx",
                 x=0.01, ha="left", fontsize=13, fontweight="semibold")
    fig.text(0.01, 0.89, "Median hours to close, NYPD's three highest-volume complaint types",
             color=INK_2, fontsize=9.5)
    fig.subplots_adjust(top=0.76, wspace=0.35)
    _source(fig)
    return fig
