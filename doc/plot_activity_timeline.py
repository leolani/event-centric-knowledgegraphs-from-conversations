import sys
import textwrap
from collections import defaultdict

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

AGENT_SOURCE = "agent"
AGENT_COLOR = "steelblue"
AGENT_MARKER = "^"   # triangle for the agent/coach
PERSON_MARKER = "o"  # circle for the patient/person

SOURCE_COLORS = {
    "agent": AGENT_COLOR,
    "Jan": "tomato",
}

# Distinct, non-blue palette for person sources so they never collide with
# the agent's blue triangle, even when a person happens to land on the
# colormap slot that would otherwise echo AGENT_COLOR.
PERSON_COLOR_PALETTE = [
    "tomato", "seagreen", "darkorange", "orchid",
    "goldenrod", "slategray", "deeppink", "indigo",
]

WRAP_WIDTH = 20  # characters per line before wrapping
GAP_DAYS = 120  # stagger labels only within local time clusters
OFFSETS = [18, -18, 42, -42, 66, -66]  # capped: max ±66 pts from dot
LABEL_FONTSIZE = 9

# Valence ordering for the GoEmotions categories emitted by GoEmotionDetector
# (see events_to_capsules.get_utterance_perspective), grouped negative →
# neutral/ambiguous → positive, per the sentiment grouping in the GoEmotions
# paper (Demszky et al. 2020). UNDERSPECIFIED (no clear emotion detected) and
# NEUTRAL sit in the middle alongside the ambiguous categories.
EMOTION_SCALE = [
    "DISAPPROVAL", "ANNOYANCE", "ANGER", "DISGUST", "GRIEF", "SADNESS",
    "DISAPPOINTMENT", "EMBARRASSMENT", "REMORSE", "NERVOUSNESS", "FEAR",
    "CONFUSION", "CURIOSITY", "SURPRISE", "REALIZATION", "UNDERSPECIFIED", "NEUTRAL",
    "APPROVAL", "RELIEF", "GRATITUDE", "ADMIRATION", "PRIDE", "CARING",
    "OPTIMISM", "DESIRE", "LOVE", "JOY", "EXCITEMENT", "AMUSEMENT",
]

# Each dimension reads a different GRASP attribution (grasp_type) off the
# utterance and plots it against its own ordered scale. "polarity" and
# "certainty" both read from "factuality": the GRASP perspective pushed to
# the KG (see events_to_capsules.get_utterance_perspective) merges those two
# into a single factuality value, so there is no separate column for either.
DIMENSIONS = {
    "level": {
        "grasp_type": "level",
        "scale": ["NOT", "ALMOST_NOT", "SOMEWHAT", "QUITE", "MOSTLY", "ALMOST_FULLY", "FULLY"],
        "ylabel": "GRASP Level",
        "title": "Activity Timeline by GRASP Level",
    },
    "sentiment": {
        "grasp_type": "sentiment",
        "scale": ["NEGATIVE", "UNDERSPECIFIED", "POSITIVE"],
        "ylabel": "Sentiment",
        "title": "Activity Timeline by Sentiment",
    },
    "polarity": {
        "grasp_type": "factuality",
        "scale": ["NEGATIVE", "UNDERSPECIFIED", "PROBABLE", "POSITIVE"],
        "ylabel": "Factuality (Polarity)",
        "title": "Activity Timeline by Factuality (Polarity)",
    },
    "certainty": {
        "grasp_type": "factuality",
        "scale": ["NEGATIVE", "UNDERSPECIFIED", "PROBABLE", "POSITIVE"],
        "ylabel": "Factuality (Certainty)",
        "title": "Activity Timeline by Factuality (Certainty)",
    },
    "emotion": {
        "grasp_type": "emotion",
        "scale": EMOTION_SCALE,
        "ylabel": "Emotion (negative → positive)",
        "title": "Activity Timeline by Emotion",
    },
}


def extract_grasp_type(url):
    fragment = url.split("#")[0]
    return fragment.split("/")[-1]

def extract_value(url):
    return url.split("#")[-1]

def source_label(url):
    return url.split("/")[-1]

def patient_label(url):
    return "" if pd.isna(url) else url.split("/")[-1]

def wrap_label(text, width=WRAP_WIDTH):
    return "\n".join(textwrap.wrap(text, width))

def slot_to_offset(idx):
    return OFFSETS[min(idx, len(OFFSETS) - 1)]


def load_data(input_file):
    df = pd.read_csv(input_file)
    df["time"] = pd.to_datetime(df["time"])
    df["grasp_type"] = df["perspective"].apply(extract_grasp_type)
    df["grasp_value"] = df["perspective"].apply(extract_value)
    df["source_label"] = df["source"].apply(source_label)
    if "patient" in df.columns:
        df["patient_label"] = df["patient"].apply(patient_label)
        df["activity_label"] = df.apply(
            lambda r: f"{r['activity']}_{r['patient_label']}" if r["patient_label"] else r["activity"],
            axis=1,
        )
    else:
        df["activity_label"] = df["activity"]
    return df


def plot_dimension(df, config, output_file):
    scale = config["scale"]
    order = {name: i for i, name in enumerate(scale)}

    rows = df[df["grasp_type"] == config["grasp_type"]].copy()
    rows["value_numeric"] = rows["grasp_value"].map(order)
    rows = rows.dropna(subset=["value_numeric"])
    if rows.empty:
        print(f"No '{config['grasp_type']}' attributions found, skipping {output_file}")
        return

    all_sources = sorted(rows["source_label"].unique())
    person_sources = [s for s in all_sources if s != AGENT_SOURCE]
    colors = {}
    markers = {}
    for s in all_sources:
        if s == AGENT_SOURCE:
            colors[s] = SOURCE_COLORS.get(s, AGENT_COLOR)
            markers[s] = AGENT_MARKER
        else:
            idx = person_sources.index(s)
            colors[s] = SOURCE_COLORS.get(s, PERSON_COLOR_PALETTE[idx % len(PERSON_COLOR_PALETTE)])
            markers[s] = PERSON_MARKER

    fig, ax = plt.subplots(figsize=(28, 10))

    # Collect all annotations, sorted by (value, time) so we can assign
    # interleaved above/below slots per value — this prevents labels at
    # similar timestamps from all fanning into the same diagonal band.
    all_annotations = []
    for source in all_sources:
        color = colors[source]
        marker = markers[source]
        subset = rows[rows["source_label"] == source].sort_values("time")
        ax.scatter(subset["time"], subset["value_numeric"], color=color, marker=marker, s=80,
                   zorder=3, label=source)
        for _, row in subset.iterrows():
            all_annotations.append((row, color))

    all_annotations.sort(key=lambda x: (x[0]["value_numeric"], x[0]["time"]))

    # Assign stagger slots only within local clusters: reset the slot counter
    # whenever consecutive labels at the same value are more than GAP_DAYS apart.
    value_last_time = {}
    value_slot = defaultdict(int)

    for row, color in all_annotations:
        val = row["value_numeric"]
        t = row["time"]
        last_t = value_last_time.get(val)
        if last_t is None or (t - last_t).days > GAP_DAYS:
            value_slot[val] = 0  # reset: this point is far from its predecessor
        value_last_time[val] = t

        slot_idx = value_slot[val]
        value_slot[val] += 1

        y_offset = slot_to_offset(slot_idx)
        va = "bottom" if y_offset > 0 else "top"
        label = wrap_label(row["activity_label"])

        ax.annotate(
            label,
            xy=(row["time"], row["value_numeric"]),
            xytext=(4, y_offset),
            textcoords="offset points",
            ha="left",
            va=va,
            fontsize=LABEL_FONTSIZE,
            rotation=45,
            rotation_mode="anchor",
            color=color,
            linespacing=1.2,
        )

    ax.set_yticks(range(len(scale)))
    ax.set_yticklabels([f"{name} ({i})" for i, name in enumerate(scale)])
    ax.set_ylim(-1.5, len(scale) - 0.5)
    ax.set_xlabel("Time")
    ax.set_ylabel(config["ylabel"])
    ax.set_title(config["title"])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate()
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.legend(title="Source")

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved to {output_file}")


def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else "query-result.csv"
    dimensions = sys.argv[2:] if len(sys.argv) > 2 else list(DIMENSIONS.keys())

    df = load_data(input_file)
    stem = input_file[:-4] if input_file.lower().endswith(".csv") else input_file
    for dimension in dimensions:
        config = DIMENSIONS[dimension]
        output_file = f"{stem}_{dimension}_timeline.png"
        plot_dimension(df, config, output_file)


if __name__ == "__main__":
    main()
