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

def extract_grasp_type(url):
    fragment = url.split("#")[0]
    return fragment.split("/")[-1]

def extract_value(url):
    return url.split("#")[-1]

def source_label(url):
    return url.split("/")[-1]

df = pd.read_csv("query-result.csv")
df["time"] = pd.to_datetime(df["time"])
df["grasp_type"] = df["perspective"].apply(extract_grasp_type)
df["grasp_value"] = df["perspective"].apply(extract_value)
df["source_label"] = df["source"].apply(source_label)

levels = df[df["grasp_type"] == "level"].copy()
levels["level_numeric"] = levels["grasp_value"].map(LEVEL_ORDER)

fig, ax = plt.subplots(figsize=(12, 5))

for source, color in SOURCE_COLORS.items():
    subset = levels[levels["source_label"] == source]
    ax.scatter(subset["time"], subset["level_numeric"], color=color, s=80,
               zorder=3, label=source)
    for _, row in subset.iterrows():
        ax.annotate(
            row["activity"],
            xy=(row["time"], row["level_numeric"]),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            fontsize=8,
            color=color,
        )

ax.set_yticks(range(5))
ax.set_yticklabels(["NOT (0)", "SOMEWHAT (1)", "QUITE (2)", "MOSTLY (3)", "ALMOST_FULLY (4)"])
ax.set_xlabel("Time")
ax.set_ylabel("GRASP Level")
ax.set_title("Activity Timeline by GRASP Level")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
fig.autofmt_xdate()
ax.grid(True, axis="y", linestyle="--", alpha=0.5)
ax.legend(title="Source")

plt.tight_layout()
plt.savefig("activity_timeline.png", dpi=150)
print("Saved to activity_timeline.png")
