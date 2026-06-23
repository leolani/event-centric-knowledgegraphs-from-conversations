"""Visualise the ECKG ontology hierarchy read from eckg_hierarchy.ttl."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Colours ───────────────────────────────────────────────────────────────────
ROOT_COL     = "#2c3e50"
L1_BLUE      = "#2980b9"
L1_GREEN     = "#27ae60"
L1_PURP      = "#8e44ad"
ACT_MID      = "#5dade2"
ACT_LEAF     = "#aed6f1"
ENT_COL      = "#a9dfbf"
TMP_COL      = "#d7bde2"
ALIGN_EQ_COL = "#1e6b3c"   # dark green — equivalentClass / exactMatch
ALIGN_CL_COL = "#935116"   # dark amber — closeMatch

# ── Leaf layout ───────────────────────────────────────────────────────────────
G  = 0.040
X0 = 0.015

def lx(i):
    return round(X0 + i * G, 4)

# (display_label, leaf_index, count, parent_L2, examples, align)
ACT_LEAVES = [
    ("Exercise",        0, 1050, "Exercise",  "walk, cycle",     "≈ n2mu:sport"),
    ("Physical\nCond.", 1,  676, "Condition", "feel, tired",     "≈ n2mu:feel"),
    ("Mental\nCond.",   2,  259, "Condition", "worry, stress",   "≈ n2mu:feel"),
    ("Social\nCond.",   3,   10, "Condition", "smoking",         None),
    ("Advise",          4,  629, "Advise",    "try, discuss",    None),
    ("Diet\n(general)", 5,  426, "Diet",      "diet, eat",       None),
    ("Take Food",       6,  421, "Diet",      "eat, have",       "= n2mu:eat"),
    ("Take Drink",      7,   35, "Diet",      "drink, tea",      "= n2mu:drink"),
    ("Social",          8,   84, "Social",    "talk, fast",      "≈ n2mu:party"),
    ("Treatment",       9,  196, "Medical",   "take, quit",      None),
    ("Measurement",    10,  168, "Medical",   "check, monitor",  None),
    ("Symptom",        11,   88, "Medical",   "fatigue, thirst", None),
    ("Medicine",       12,    4, "Medical",   "medication",      None),
    ("Disease",        13,    2, "Medical",   "nerve damage",    None),
]

# (label, x, count, kind, examples, align)
ACT_L2 = [
    ("Exercise",  lx(0),              1050, "leaf", None, "≈ n2mu:sport"),
    ("Condition", (lx(1)+lx(3))/2,    945,  "mid",  None, "≈ n2mu:feel"),
    ("Advise",    lx(4),               629, "leaf", None, None),
    ("Diet",      (lx(5)+lx(7))/2,    882,  "mid",  None, "≈ n2mu:have-meal"),
    ("Social",    lx(8),               84,  "leaf", None, "≈ n2mu:party"),
    ("Medical",   (lx(9)+lx(13))/2,   458,  "mid",  None, None),
]
ACT_L1_X = (lx(0) + lx(13)) / 2

COL_ENT = 0.710
GAP_E   = 0.050
# (label, count, examples, align)
ENT_ROW1 = [
    ("Person",   3908, "Jan, Aicha",     "≡ n2mu:person"),
    ("Food",      880, "baklava, dates", "≈ n2mu:food"),
    ("Other",     592, None,             None),
    ("Body Part", 537, "blood sugar",    None),
    ("Concept",   387, "monitoring",     None),
    ("Location",  333, "indoor, Dutch",  "≡ n2mu:location"),
]
ENT_ROW2 = [
    ("Activity",  244, "brisk walking",  "≈ n2mu:do-activity"),
    ("Device",    115, "glucometer",     "≡ n2mu:device"),
    ("Medication", 72, "insulin",        None),
    ("Quantity",   59, "15g carbs",      None),
    ("Time",        8, "morning",        "≈ sem:Time"),
    ("Meal",        2, "dinner",         "≈ n2mu:dish"),
]

COL_TMP = 0.958
GAP_T   = 0.040
# (label, count, examples, align)
TMP_LEAVES = [
    ("Vague",    1019, "recently, often", None),
    ("Recurring", 716, "daily, weekly",   None),
    ("Range",     622, "this week",       None),
    ("Point",      19, "today, now",      None),
]

# Y-levels
Y_ROOT = 0.95
Y_L1   = 0.84
Y_L2   = 0.72
Y_L3   = 0.52
Y_ENT2 = 0.52

# Node dimensions
W_L3 = 0.044
H_L3 = 0.090
W_L2 = 0.058
H_L2 = 0.084

# ── Drawing helpers ───────────────────────────────────────────────────────────

def draw_box(ax, x, y, label, count, examples, facecolor,
             fs_label=16, fs_count=26, fs_ex=20, fs_align=15,
             width=W_L3, height=H_L3, label_color="#111", align=None):
    ax.add_patch(FancyBboxPatch(
        (x - width/2, y - height/2), width, height,
        boxstyle="round,pad=0.010", linewidth=0.9,
        edgecolor="#555", facecolor=facecolor, zorder=3
    ))
    items = [("label", label), ("count", count)]
    items = [(k, v) for k, v in items if v is not None]
    n = sum(label.count("\n") + 1 if k == "label" else 1 for k, v in items)
    step = height / (n + 1)
    cy = y + height/2 - step
    for k, v in items:
        if k == "label":
            ax.text(x, cy, v, ha="center", va="center",
                    fontsize=fs_label, fontweight="bold",
                    color=label_color, zorder=4, linespacing=1.15)
            cy -= step * (v.count("\n") + 1)
        elif k == "count":
            ax.text(x, cy, f"n={v:,}", ha="center", va="center",
                    fontsize=fs_count, color="#333", zorder=4)
    # Examples as italic text below box
    offset = -0.016
    if examples:
        ax.text(x, y - height/2 + offset, examples,
                ha="center", va="top",
                fontsize=fs_ex, color="#444", style="italic", zorder=4)
        offset -= 0.024
    # Alignment annotation in monospace below examples
    if align:
        col = ALIGN_EQ_COL if align[0] in ("≡", "=") else ALIGN_CL_COL
        ax.text(x, y - height/2 + offset, align,
                ha="center", va="top",
                fontsize=fs_align, color=col,
                fontfamily="monospace", zorder=4)

def edge(ax, x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color="#aaa", linewidth=0.8, zorder=1)

def spread(n, cx, gap):
    return [cx - (n-1)*gap/2 + i*gap for i in range(n)]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    fig, ax = plt.subplots(figsize=(42, 23))
    ax.set_xlim(-0.01, 1.03)
    ax.set_ylim(0.30, 1.01)
    ax.axis("off")
    fig.patch.set_facecolor("#f5f5f5")

    # ── owl:Thing root ────────────────────────────────────────────────────────
    draw_box(ax, 0.5, Y_ROOT, "owl:Thing", None, None,
             ROOT_COL, fs_label=32, width=0.22, height=0.080, label_color="white")

    # ── Level 1 ───────────────────────────────────────────────────────────────
    L1_CONFIG = [
        (ACT_L1_X, "ActivityType", L1_BLUE,  "≈ n2mu:do-activity"),
        (COL_ENT,  "EntityType",   L1_GREEN, None),
        (COL_TMP,  "TemporalType", L1_PURP,  "≈ sem:Time"),
    ]
    for cx, lbl, col, al in L1_CONFIG:
        edge(ax, 0.5, Y_ROOT-0.040, cx, Y_L1+0.034)
        draw_box(ax, cx, Y_L1, lbl, None, None, col,
                 fs_label=26, fs_align=16, width=0.20, height=0.068,
                 label_color="white", align=al)

    # ── ActivityType L2 ───────────────────────────────────────────────────────
    for lbl, ax_x, count, kind, ex, al in ACT_L2:
        edge(ax, ACT_L1_X, Y_L1-0.034, ax_x, Y_L2+0.034)
        fc = ACT_MID if kind == "mid" else ACT_LEAF
        draw_box(ax, ax_x, Y_L2, lbl, count, ex,
                 fc, fs_label=18, fs_count=28, fs_ex=11, fs_align=14,
                 width=W_L2, height=H_L2, align=al)

    # ── ActivityType L3 (children of Condition, Diet, Medical) ────────────────
    L2_LEAVES = {r[0] for r in ACT_L2 if r[3] == "leaf"}
    parent_x_of = {lbl: ax_x for lbl, ax_x, _, kind, _, _ in ACT_L2 if kind == "mid"}

    for lbl, idx, count, parent_key, ex, al in ACT_LEAVES:
        if parent_key in L2_LEAVES:
            continue
        px = parent_x_of[parent_key]
        cx = lx(idx)
        edge(ax, px, Y_L2-0.034, cx, Y_L3+0.046)
        draw_box(ax, cx, Y_L3, lbl, count, ex,
                 ACT_LEAF, fs_label=16, fs_count=26, fs_ex=20, fs_align=15,
                 width=W_L3, height=H_L3, align=al)

    # ── EntityType leaves ─────────────────────────────────────────────────────
    for row, y_row in [(ENT_ROW1, Y_L2), (ENT_ROW2, Y_ENT2)]:
        for (lbl, cnt, ex, al), cx in zip(row, spread(len(row), COL_ENT, GAP_E)):
            edge(ax, COL_ENT, Y_L1-0.034, cx, y_row+0.046)
            draw_box(ax, cx, y_row, lbl, cnt, ex,
                     ENT_COL, fs_label=16, fs_count=26, fs_ex=20, fs_align=15,
                     width=W_L3, height=H_L3, align=al)

    # ── TemporalType leaves ───────────────────────────────────────────────────
    for (lbl, cnt, ex, al), cx in zip(TMP_LEAVES, spread(len(TMP_LEAVES), COL_TMP, GAP_T)):
        edge(ax, COL_TMP, Y_L1-0.034, cx, Y_L2+0.046)
        draw_box(ax, cx, Y_L2, lbl, cnt, ex,
                 TMP_COL, fs_label=16, fs_count=26, fs_ex=20, fs_align=15,
                 width=W_L3, height=H_L3, align=al)

    # ── Separators & legend ───────────────────────────────────────────────────
    for xv in [0.60, 0.888]:
        ax.axvline(xv, color="#ccc", linewidth=1, linestyle="--", zorder=0)

    ax.legend(handles=[
        mpatches.Patch(facecolor=ACT_MID,  edgecolor="#555", label="Activity group (intermediate)"),
        mpatches.Patch(facecolor=ACT_LEAF, edgecolor="#555", label="Activity type (leaf)"),
        mpatches.Patch(facecolor=ENT_COL,  edgecolor="#555", label="Entity / role type"),
        mpatches.Patch(facecolor=TMP_COL,  edgecolor="#555", label="Temporal type"),
    ], loc="lower right", fontsize=15, framealpha=0.95, edgecolor="#ccc")

    # ── Alignment notation key ────────────────────────────────────────────────
    ax.text(0.01, 0.012,
            "n2mu alignment:   ≡ owl:equivalentClass   = skos:exactMatch   ≈ skos:closeMatch",
            ha="left", va="bottom", fontsize=14, color="#555",
            fontfamily="monospace", transform=ax.transAxes)

    ax.set_title(
        "Event-Centric Knowledge Graph — Concept Hierarchy with Frequency Counts and Examples",
        fontsize=22, fontweight="bold", pad=12, color="#2c3e50"
    )

    out = "doc/eckg_hierarchy.png"
    plt.tight_layout()
    plt.savefig(out, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(f"Saved → {out}")

if __name__ == "__main__":
    main()
