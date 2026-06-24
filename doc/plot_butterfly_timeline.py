"""
plot_butterfly_timeline.py — Vertical butterfly activity timeline.

Layout
------
• Y-axis  : time (earlier at top, later at bottom — scrollable vertically)
• X = 0   : centre line where activities are plotted as ◆ diamonds
• X > 0   : positive emotions (right half)
• X < 0   : negative emotions (left half)
• Activity labels are horizontal, alternating right / left of the centre line
• Marker shapes / colours distinguish the two speakers (Rudolf / agent)

Usage
-----
    python plot_butterfly_timeline.py [query-result-rudolf.csv]
"""

import argparse
import sys
import textwrap

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches

# ── Emotion scale (negative → neutral → positive) ─────────────────────────────
EMOTION_SCALE = [
    "DISAPPROVAL", "ANNOYANCE", "ANGER", "DISGUST", "GRIEF", "SADNESS",
    "DISAPPOINTMENT", "EMBARRASSMENT", "REMORSE", "NERVOUSNESS", "FEAR",
    "CONFUSION", "CURIOSITY", "SURPRISE", "REALIZATION", "UNDERSPECIFIED", "NEUTRAL",
    "APPROVAL", "RELIEF", "GRATITUDE", "ADMIRATION", "PRIDE", "CARING",
    "OPTIMISM", "DESIRE", "LOVE", "JOY", "EXCITEMENT", "AMUSEMENT",
]
_NEUTRAL_IDX = EMOTION_SCALE.index("UNDERSPECIFIED")
_EMOTION_X_RAW = {e: i - _NEUTRAL_IDX for i, e in enumerate(EMOTION_SCALE)}

EMOTION_X_SCALE = 0.30   # tighter spacing so all emotions fit in A4 width
EMOTION_X = {e: v * EMOTION_X_SCALE for e, v in _EMOTION_X_RAW.items()}

EXCLUDE_EMOTIONS = {"UNDERSPECIFIED", "NEUTRAL"}

# ── Paper format: width (portrait, inches) and font/marker scale vs A4 ────────
DIM_CONFIG = {
    "a4": {"width":  8.27, "scale": 1.00},   # 210 mm
    "a3": {"width": 11.69, "scale": 1.41},   # 297 mm  (√2 × A4)
    "a1": {"width": 23.39, "scale": 2.83},   # 594 mm  (2√2 × A4)
}

# ── Activity-type colours ─────────────────────────────────────────────────────
ACTIVITY_TYPE_COLORS = {
    "food / diet":         "#F57C00",
    "exercise":            "#388E3C",
    "health monitoring":   "#5C6BC0",
    "symptoms":            "#C62828",
    "lifestyle / social":  "#6A1B9A",
}

# ── Speaker colours and marker shapes ────────────────────────────────────────
SPEAKER_COLORS  = {"Rudolf": "#D50000", "agent": "#0097A7"}
SPEAKER_MARKERS = {"Rudolf": "o", "agent": "^"}
# Offset speakers' emotion markers in the time (Y) direction to avoid overlap
SOURCE_Y_OFFSET_DAYS = {"Rudolf": -20, "agent": +20}

SPREAD_DAYS = 24   # days between diamonds sharing the same calendar date

# ── Base font sizes (A4 reference — scaled up for larger formats) ─────────────
ACTIVITY_LABEL_FS = 16
EMOTION_LABEL_FS  = 10
YTICK_FS          = 10
XTICK_FS          = 9
LEGEND_FS         = 10
LEGEND_TITLE_FS   = 11
AXIS_LABEL_FS     = 12
TITLE_FS          = 13
ZONE_LABEL_FS     = 10

WRAP_WIDTH = 22


# ── Helpers ───────────────────────────────────────────────────────────────────
def _grasp_type(url):   return url.split("#")[0].split("/")[-1]
def _grasp_value(url):  return url.split("#")[-1]
def _source_label(url): return url.split("/")[-1]
def _wrap(text, width=WRAP_WIDTH):
    return "\n".join(textwrap.wrap(text, width))


def classify_activity(name):
    a = name.lower()
    if any(k in a for k in ["blood sugar", "blood glucose", "glucose level",
                              "log glucose", "check blood", "checking", "monitor",
                              "check"]):
        return "health monitoring"
    if any(k in a for k in ["cramp", "pain", "tired", "thirst", "weight loss",
                              "lost a few", "washroom", "lightheaded", "spike",
                              "excessive", "needing to go", "muscle", "feeling",
                              "foot"]):
        return "symptoms"
    if any(k in a for k in ["cycl", "exercis", "moving around", "physical activity",
                              "child's pose", "moderate-intensity"]):
        return "exercise"
    if any(k in a for k in ["eat", "eating", "food", "breakfast", "dinner", "supper",
                              "snack", "meal", "fruit", "protein", "apple", "coffee",
                              "consuming", "portion", "adjust my meals", "balance meals"]):
        return "food / diet"
    return "lifestyle / social"


def load_data(path):
    df = pd.read_csv(path)
    df["time"]         = pd.to_datetime(df["time"])
    df["grasp_type"]   = df["perspective"].apply(_grasp_type)
    df["grasp_value"]  = df["perspective"].apply(_grasp_value)
    df["source_label"] = df["source"].apply(_source_label)
    df["date_floor"]   = df["time"].dt.floor("D")
    return df


def _spread_events(events, spread_days=SPREAD_DAYS):
    """Spread diamonds sharing the same calendar date vertically (in time)."""
    events = events.copy().reset_index(drop=True)
    events["plot_time"] = events["evt_time"]
    for _, grp in events.groupby("date_floor"):
        n = len(grp)
        if n > 1:
            half = (n - 1) * spread_days / 2.0
            for i, idx in enumerate(grp.index):
                events.at[idx, "plot_time"] = (
                    events.at[idx, "evt_time"] + pd.Timedelta(days=-half + i * spread_days)
                )
    return events


def _assign_label_dirs(events):
    """
    Alternate label direction within each date cluster.
    +1 → RIGHT (positive-emotion side), -1 → LEFT (negative-emotion side).
    """
    events = (events
              .sort_values(["date_floor", "atype", "activity"])
              .reset_index(drop=True))
    events["label_dir"] = 1
    for _, grp in events.groupby("date_floor"):
        dirs = [1 if i % 2 == 0 else -1 for i in range(len(grp))]
        events.loc[grp.index, "label_dir"] = dirs
    return events


# ── Main plot ─────────────────────────────────────────────────────────────────
def plot_butterfly(df, output_file, dim="a4"):
    # --- Emotion rows ---------------------------------------------------------
    emo = df[df["grasp_type"] == "emotion"].copy()
    emo = emo[~emo["grasp_value"].isin(EXCLUDE_EMOTIONS)]
    emo["ex"] = emo["grasp_value"].map(EMOTION_X)   # X position on emotion axis
    emo = emo.dropna(subset=["ex"])

    data_emotions = set(emo["grasp_value"].unique())
    display_emotions = [e for e in EMOTION_SCALE
                        if e not in EXCLUDE_EMOTIONS and e in data_emotions]

    # --- Activity events ------------------------------------------------------
    events = (
        df.groupby(["activity", "date_floor"])["time"]
          .first()
          .reset_index()
          .rename(columns={"time": "evt_time"})
    )
    events["atype"] = events["activity"].apply(classify_activity)
    events = _spread_events(events)
    events = _assign_label_dirs(events)

    plot_time_lookup = {
        (r["activity"], r["date_floor"]): r["plot_time"]
        for _, r in events.iterrows()
    }
    emo["base_plot_time"] = emo.apply(
        lambda r: plot_time_lookup.get((r["activity"], r["date_floor"]), r["time"]),
        axis=1,
    )

    # --- X-axis extents: tight around actual emotions, use full A4 width ------
    pos_xs = [EMOTION_X[e] for e in display_emotions if EMOTION_X[e] > 0]
    neg_xs = [EMOTION_X[e] for e in display_emotions if EMOTION_X[e] < 0]
    xmax = (max(pos_xs) + 0.35) if pos_xs else 1.0
    xmin = (min(neg_xs) - 0.35) if neg_xs else -1.0
    first_pos_x = min(pos_xs) if pos_xs else 0.3
    first_neg_x = max(neg_xs) if neg_xs else -0.3

    # --- Figure: format-dependent width, tall for vertical scrolling ----------
    cfg  = DIM_CONFIG[dim]
    fw   = cfg["width"]    # figure width in inches
    sc   = cfg["scale"]    # linear scale factor relative to A4

    date_range_days = (events["plot_time"].max() - events["plot_time"].min()).days
    fig_height = max(24 * sc, int(date_range_days / 30) * 3 * sc)
    fig, ax = plt.subplots(figsize=(fw, fig_height))
    plt.rcParams.update({"font.size": 10 * sc})

    # Zone shading — right = positive, left = negative
    ax.axvspan(first_pos_x, xmax, alpha=0.05, color="#66BB6A", zorder=0)
    ax.axvspan(xmin, first_neg_x, alpha=0.05, color="#EF5350", zorder=0)
    ax.axvline(0, color="#888", linewidth=1.2, alpha=0.55, zorder=1)

    # --- Activity diamonds + horizontal left/right labels --------------------
    LABEL_X_OFFSET = 0.25 * EMOTION_X_SCALE

    for _, row in events.iterrows():
        t         = row["plot_time"]
        color     = ACTIVITY_TYPE_COLORS[row["atype"]]
        label_dir = int(row["label_dir"])   # +1 = right, -1 = left

        # Diamond on the centre line at Y = time
        ax.scatter(0, t, color=color, s=230*sc**2, zorder=5, marker="D",
                   edgecolors="white", linewidth=0.9*sc)

        label_text = _wrap(row["activity"])
        if label_dir > 0:
            ax.annotate(
                label_text,
                xy=(LABEL_X_OFFSET, t),
                xytext=(5*sc, 0),
                textcoords="offset points",
                ha="left", va="center",
                fontsize=ACTIVITY_LABEL_FS*sc,
                color=color, fontstyle="italic",
                rotation=0,
            )
        else:
            ax.annotate(
                label_text,
                xy=(-LABEL_X_OFFSET, t),
                xytext=(-5*sc, 0),
                textcoords="offset points",
                ha="right", va="center",
                fontsize=ACTIVITY_LABEL_FS*sc,
                color=color, fontstyle="italic",
                rotation=0,
            )

    # --- Emotion markers -------------------------------------------------------
    all_sources = sorted(emo["source_label"].unique())

    for _, row in emo.iterrows():
        source = row["source_label"]
        ex     = float(row["ex"])
        base_t = row["base_plot_time"]

        sp_color = SPEAKER_COLORS.get(source, "#555")
        marker   = SPEAKER_MARKERS.get(source, "o")
        # Offset speakers vertically (in time) to separate overlapping markers
        t_plot   = base_t + pd.Timedelta(days=SOURCE_Y_OFFSET_DAYS.get(source, 0))

        # Horizontal line from centre to marker
        ax.plot([0, ex], [t_plot, t_plot],
                color=sp_color, alpha=0.20, linewidth=0.9*sc, zorder=2)
        ax.scatter(ex, t_plot, color=sp_color, marker=marker, s=85*sc**2,
                   alpha=0.88, zorder=4, edgecolors="white", linewidth=0.4*sc)

        # Emotion name radiates outward from centre (right for positive, left for negative)
        ha    = "left"  if ex >= 0 else "right"
        x_off = 4*sc    if ex >= 0 else -4*sc
        ax.annotate(
            row["grasp_value"],
            xy=(ex, t_plot),
            xytext=(x_off, 0),
            textcoords="offset points",
            fontsize=EMOTION_LABEL_FS*sc,
            color=sp_color, ha=ha, va="center",
        )

    # --- X axis: emotion scale at the top of the graph -----------------------
    ax.set_xticks([EMOTION_X[e] for e in display_emotions])
    ax.set_xticklabels(display_emotions, fontsize=XTICK_FS*sc, rotation=45, ha="left")
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set_xlim(xmin, xmax)
    ax.set_xlabel("Emotion", fontsize=AXIS_LABEL_FS*sc)
    ax.grid(True, axis="x", linestyle=":", alpha=0.3)

    # --- Y axis: time (earlier at top, no empty lead-in) ---------------------
    ax.yaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.yaxis.set_major_locator(mdates.MonthLocator())
    ax.tick_params(axis="y", labelsize=YTICK_FS*sc)
    ax.set_ylabel("Time", fontsize=AXIS_LABEL_FS*sc)
    pad = pd.Timedelta(days=15)
    ax.set_ylim(events["plot_time"].min() - pad, events["plot_time"].max() + pad)
    ax.invert_yaxis()   # earliest date at top → natural reading order
    ax.grid(True, axis="y", linestyle=":", alpha=0.3)

    # Zone labels in axes coordinates so they stay fixed regardless of data range
    ax.text(0.97, 0.005, "positive emotions →",
            color="#2E7D32", fontsize=ZONE_LABEL_FS*sc, alpha=0.75,
            ha="right", va="bottom", transform=ax.transAxes)
    ax.text(0.03, 0.005, "← negative emotions",
            color="#B71C1C", fontsize=ZONE_LABEL_FS*sc, alpha=0.75,
            ha="left", va="bottom", transform=ax.transAxes)

    ax.set_title(
        "Activity Timeline — Emotion Perspectives by Speaker\n"
        "◆ activity (coloured by type)   ○ = Rudolf   △ = agent",
        fontsize=TITLE_FS*sc,
    )

    # --- Legends ---------------------------------------------------------------
    type_handles = [
        mpatches.Patch(color=c, label=lbl)
        for lbl, c in ACTIVITY_TYPE_COLORS.items()
    ]
    speaker_handles = [
        plt.Line2D([0], [0], marker=SPEAKER_MARKERS.get(s, "o"), color="w",
                   markerfacecolor=SPEAKER_COLORS.get(s, "#555"),
                   markersize=11*sc, label=s)
        for s in (all_sources or list(SPEAKER_COLORS))
    ]
    leg1 = ax.legend(handles=type_handles, title="Activity type",
                     loc="upper left", fontsize=LEGEND_FS*sc,
                     title_fontsize=LEGEND_TITLE_FS*sc, framealpha=0.9)
    ax.add_artist(leg1)
    ax.legend(handles=speaker_handles, title="Speaker",
              loc="upper right", fontsize=LEGEND_FS*sc,
              title_fontsize=LEGEND_TITLE_FS*sc, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {output_file}")


def main():
    p = argparse.ArgumentParser(
        description="Vertical butterfly activity timeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input_file", nargs="?", default="query-result-rudolf.csv",
                   help="CSV file produced by the SPARQL query")
    p.add_argument("--dim", choices=list(DIM_CONFIG), default="a4",
                   help="Output paper format (a4 / a3 / a1)")
    args = p.parse_args()

    df   = load_data(args.input_file)
    stem = args.input_file[:-4] if args.input_file.lower().endswith(".csv") else args.input_file
    plot_butterfly(df, f"{stem}_butterfly_timeline.png", dim=args.dim)


if __name__ == "__main__":
    main()