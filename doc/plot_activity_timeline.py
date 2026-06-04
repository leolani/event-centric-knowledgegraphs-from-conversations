import sys
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

LEVEL_ORDER = {
    "NOT": 0,
    "SOMEWHAT": 1,
    "QUITE": 2,
    "MOSTLY": 3,
    "ALMOST_FULLY": 4,
    "FULLY": 4,
}

SOURCE_COLORS = {
    "agent": "steelblue",
    "Jan": "tomato",
}

WRAP_WIDTH = 20  # characters per line before wrapping

def extract_grasp_type(url):
    fragment = url.split("#")[0]
    return fragment.split("/")[-1]

def extract_value(url):
    return url.split("#")[-1]

def source_label(url):
    return url.split("/")[-1]

def patient_label(url):
    return url.split("/")[-1]

def wrap_label(text, width=WRAP_WIDTH):
    return "\n".join(textwrap.wrap(text, width))

input_file = sys.argv[1] if len(sys.argv) > 1 else "query-result.csv"
output_file = input_file.replace(".csv", "_timeline.png")

df = pd.read_csv(input_file)
df["time"] = pd.to_datetime(df["time"])
df["grasp_type"] = df["perspective"].apply(extract_grasp_type)
df["grasp_value"] = df["perspective"].apply(extract_value)
df["source_label"] = df["source"].apply(source_label)
df["patient_label"] = df["patient"].apply(patient_label)
df["activity_label"] = df["activity"] + "_" + df["patient_label"]

levels = df[df["grasp_type"] == "level"].copy()
levels["level_numeric"] = levels["grasp_value"].map(LEVEL_ORDER)

all_sources = sorted(levels["source_label"].unique())
cmap = plt.get_cmap("tab10")
colors = {s: SOURCE_COLORS.get(s, cmap(i / max(len(all_sources), 1)))
          for i, s in enumerate(all_sources)}

fig, ax = plt.subplots(figsize=(28, 10))

# Collect all annotations, sorted by (level_numeric, time) so we can assign
# interleaved above/below slots per level — this prevents labels at similar
# timestamps from all fanning into the same diagonal band.
from collections import defaultdict

all_annotations = []
for source in all_sources:
    color = colors[source]
    subset = levels[levels["source_label"] == source].sort_values("time")
    ax.scatter(subset["time"], subset["level_numeric"], color=color, s=80,
               zorder=3, label=source)
    for _, row in subset.iterrows():
        all_annotations.append((row, color))

# Sort by level then time so slot indices are assigned in time order per level
all_annotations.sort(key=lambda x: (x[0]["level_numeric"], x[0]["time"]))

# Assign stagger slots only within local clusters: reset the slot counter
# whenever consecutive labels at the same level are more than GAP_DAYS apart.
GAP_DAYS = 120
OFFSETS = [12, -12, 28, -28, 44, -44]  # capped: max ±44 pts from dot

def slot_to_offset(idx):
    return OFFSETS[min(idx, len(OFFSETS) - 1)]

level_last_time = {}  # last timestamp seen per level
level_slot = defaultdict(int)

for row, color in all_annotations:
    lvl = row["level_numeric"]
    t = row["time"]
    last_t = level_last_time.get(lvl)
    if last_t is None or (t - last_t).days > GAP_DAYS:
        level_slot[lvl] = 0  # reset: this point is far from its predecessor
    level_last_time[lvl] = t

    slot_idx = level_slot[lvl]
    level_slot[lvl] += 1

    y_offset = slot_to_offset(slot_idx)
    va = "bottom" if y_offset > 0 else "top"
    label = wrap_label(row["activity_label"])

    ax.annotate(
        label,
        xy=(row["time"], row["level_numeric"]),
        xytext=(4, y_offset),
        textcoords="offset points",
        ha="left",
        va=va,
        fontsize=6,
        rotation=45,
        rotation_mode="anchor",
        color=color,
        linespacing=1.2,
    )

ax.set_yticks(range(5))
ax.set_yticklabels(["NOT (0)", "SOMEWHAT (1)", "QUITE (2)", "MOSTLY (3)", "ALMOST_FULLY (4)"])
ax.set_ylim(-1.5, 5.5)
ax.set_xlabel("Time")
ax.set_ylabel("GRASP Level")
ax.set_title("Activity Timeline by GRASP Level")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
fig.autofmt_xdate()
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
ax.legend(title="Source")

plt.tight_layout()
plt.savefig(output_file, dpi=150, bbox_inches="tight")
print(f"Saved to {output_file}")
