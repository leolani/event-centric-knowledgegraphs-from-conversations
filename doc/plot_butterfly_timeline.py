"""
plot_butterfly_timeline.py — Alternative activity timeline visualisation.

Layout
------
• X-axis  : time
• Y = 0   : centre line where activities are plotted as ◆ diamonds,
             coloured by *activity type* (food/diet, exercise, …)
• Y > 0   : positive emotions of each source about that activity
• Y < 0   : negative emotions of each source about that activity
• Marker shapes / colours distinguish the two speakers (Rudolf / agent)
• Activity labels alternate above / below the centre line so both halves
  of the whitespace carry text, halving label density in each direction.

Usage
-----
    python plot_butterfly_timeline.py [query-result-rudolf.csv]
"""

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
_EMOTION_Y_RAW = {e: i - _NEUTRAL_IDX for i, e in enumerate(EMOTION_SCALE)}

# Compress the emotion clusters toward the centre line.
# A smaller scale means each y-unit represents more physical height in the
# figure, so fixed-size activity labels cover fewer y-units before reaching
# the first emotion marker.
EMOTION_Y_SCALE = 0.5
EMOTION_Y = {e: v * EMOTION_Y_SCALE for e, v in _EMOTION_Y_RAW.items()}

# Always hidden: anchor point and its nearest neighbour (both uninformative)
EXCLUDE_EMOTIONS = {"UNDERSPECIFIED", "NEUTRAL"}

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
SOURCE_X_OFFSET_DAYS = {"Rudolf": -20, "agent": +20}

SPREAD_DAYS = 24   # days between diamonds that share the same calendar date

# ── Font sizes ────────────────────────────────────────────────────────────────
ACTIVITY_LABEL_FS = 9
EMOTION_LABEL_FS  = 9
YTICK_FS          = 10
LEGEND_FS         = 10
LEGEND_TITLE_FS   = 11
AXIS_LABEL_FS     = 12
TITLE_FS          = 14
ZONE_LABEL_FS     = 11

# Wrap only when the label would be long enough to risk collision.
# At 82° rotation a 22-char line fits in the gap between y=0 and the first
# emotion; longer phrases wrap to keep each line within that budget.
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
    """Spread diamonds that share the same calendar date horizontally."""
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
    Within each date cluster, alternate label direction: even-indexed → UP (+1),
    odd-indexed → DOWN (−1).  Sort within each cluster by type then name first
    so the alternation is visually predictable.
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
def plot_butterfly(df, output_file):
    # --- Emotion rows ---------------------------------------------------------
    emo = df[df["grasp_type"] == "emotion"].copy()
    emo = emo[~emo["grasp_value"].isin(EXCLUDE_EMOTIONS)]
    emo["ey"] = emo["grasp_value"].map(EMOTION_Y)
    emo = emo.dropna(subset=["ey"])

    # Y-axis shows only emotions that actually appear in this dataset
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

    # --- Figure extents -------------------------------------------------------
    pos_ys = [EMOTION_Y[e] for e in display_emotions if EMOTION_Y[e] > 0]
    neg_ys = [EMOTION_Y[e] for e in display_emotions if EMOTION_Y[e] < 0]
    ymax = max(pos_ys) + 1.2
    ymin = min(neg_ys) - 1.2

    # --- Figure ---------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(44, 16))
    plt.rcParams.update({"font.size": 10})

    # Zone shading — start from the first actual emotion, not y=±0.5
    first_pos = min(pos_ys)
    first_neg = max(neg_ys)
    ax.axhspan(first_pos, ymax, alpha=0.05, color="#66BB6A", zorder=0)
    ax.axhspan(ymin, first_neg, alpha=0.05, color="#EF5350", zorder=0)
    ax.axhline(0, color="#888", linewidth=1.2, alpha=0.55, zorder=1)

    # --- Activity diamonds + alternating up/down labels ----------------------
    LABEL_Y_OFFSET = 0.25 * EMOTION_Y_SCALE   # how far above/below centre the anchor sits

    for _, row in events.iterrows():
        t         = row["plot_time"]
        color     = ACTIVITY_TYPE_COLORS[row["atype"]]
        label_dir = int(row["label_dir"])   # +1 = up, -1 = down

        ax.scatter(t, 0, color=color, s=230, zorder=5, marker="D",
                   edgecolors="white", linewidth=0.9)

        if label_dir > 0:
            # Label goes nearly vertically UPWARD (82° CCW) above the diamond
            ax.annotate(
                _wrap(row["activity"]),
                xy=(t, LABEL_Y_OFFSET),
                xytext=(4, 5),
                textcoords="offset points",
                ha="left", va="bottom",
                fontsize=ACTIVITY_LABEL_FS,
                color=color, fontstyle="italic",
                rotation=82, rotation_mode="anchor",
            )
        else:
            # Label goes nearly vertically DOWNWARD (82° CW) below the diamond
            ax.annotate(
                _wrap(row["activity"]),
                xy=(t, -LABEL_Y_OFFSET),
                xytext=(4, -5),
                textcoords="offset points",
                ha="left", va="top",
                fontsize=ACTIVITY_LABEL_FS,
                color=color, fontstyle="italic",
                rotation=-82, rotation_mode="anchor",
            )

    # --- Emotion markers -----------------------------------------------------
    all_sources = sorted(emo["source_label"].unique())

    for _, row in emo.iterrows():
        source = row["source_label"]
        ey     = float(row["ey"])
        base_t = row["base_plot_time"]

        sp_color = SPEAKER_COLORS.get(source, "#555")
        marker   = SPEAKER_MARKERS.get(source, "o")
        t_plot   = base_t + pd.Timedelta(days=SOURCE_X_OFFSET_DAYS.get(source, 0))

        ax.plot([t_plot, t_plot], [0, ey],
                color=sp_color, alpha=0.20, linewidth=0.9, zorder=2)
        ax.scatter(t_plot, ey, color=sp_color, marker=marker, s=85,
                   alpha=0.88, zorder=4, edgecolors="white", linewidth=0.4)

        # Emotion text to the LEFT so it diverges from activity labels (upward-right)
        va    = "bottom" if ey >= 0 else "top"
        y_off = 4 if ey >= 0 else -4
        ax.annotate(
            row["grasp_value"],
            xy=(t_plot, ey),
            xytext=(-4, y_off),
            textcoords="offset points",
            fontsize=EMOTION_LABEL_FS,
            color=sp_color, ha="right", va=va,
        )

    # --- Y axis: only emotions present in the data ---------------------------
    ax.set_yticks([EMOTION_Y[e] for e in display_emotions])
    ax.set_yticklabels(display_emotions, fontsize=YTICK_FS)
    ax.set_ylim(ymin, ymax)

    xlim  = ax.get_xlim()
    x_min = pd.Timestamp(mdates.num2date(xlim[0]))
    ax.text(x_min, ymax - 0.1, "positive emotions ↑",
            color="#2E7D32", fontsize=ZONE_LABEL_FS, alpha=0.75, va="top")
    ax.text(x_min, ymin + 0.1, "negative emotions ↓",
            color="#B71C1C", fontsize=ZONE_LABEL_FS, alpha=0.75, va="bottom")

    # --- X axis ---------------------------------------------------------------
    ax.set_xlabel("Time", fontsize=AXIS_LABEL_FS)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.tick_params(axis="x", labelsize=10)
    fig.autofmt_xdate()
    ax.grid(True, axis="x", linestyle=":", alpha=0.3)

    ax.set_title(
        "Activity Timeline — Emotion Perspectives by Speaker\n"
        "◆ activity (coloured by type)   ○ = Rudolf   △ = agent",
        fontsize=TITLE_FS,
    )

    # --- Legends --------------------------------------------------------------
    type_handles = [
        mpatches.Patch(color=c, label=lbl)
        for lbl, c in ACTIVITY_TYPE_COLORS.items()
    ]
    speaker_handles = [
        plt.Line2D([0], [0], marker=SPEAKER_MARKERS.get(s, "o"), color="w",
                   markerfacecolor=SPEAKER_COLORS.get(s, "#555"),
                   markersize=11, label=s)
        for s in (all_sources or list(SPEAKER_COLORS))
    ]
    leg1 = ax.legend(handles=type_handles, title="Activity type",
                     loc="upper left",  fontsize=LEGEND_FS,
                     title_fontsize=LEGEND_TITLE_FS, framealpha=0.9)
    ax.add_artist(leg1)
    ax.legend(handles=speaker_handles, title="Speaker",
              loc="upper right", fontsize=LEGEND_FS,
              title_fontsize=LEGEND_TITLE_FS, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved → {output_file}")


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "query-result-rudolf.csv"
    df = load_data(input_file)
    stem = input_file[:-4] if input_file.lower().endswith(".csv") else input_file
    plot_butterfly(df, f"{stem}_butterfly_timeline.png")


if __name__ == "__main__":
    main()
