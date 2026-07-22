"""
Descriptive statistics for a manually annotated SRL conversation file (default:
../../data/annotations_piek.json), written out as a LaTeX table report (and a matching JSON
file with the same numbers). This is corpus composition, not evaluation -- how many
conversations/turns/activities/roles are annotated and which values they use -- so it only
reads one file, unlike evaluate.py which compares a gold file against a system file.

Usage:
    python annotation_statistics.py [--input PATH] [--output DIR]
"""

import argparse
import json
import os
from collections import Counter

import data_type
from evaluate import ROLE_FIELDS, esc_tex, fmt_tex, flatten_turns, load_conversations, turn_perspectives

# Roles whose filler values are typed with RoleType (person/object/tool/...); "result" has its
# own ResultType, "time" has no type at all -- see data_type.ROLE_TYPES.
ROLE_TYPE_ROLES = [r for r in ROLE_FIELDS if r not in ("result", "time")]


def compute_statistics(conversations):
    """Corpus-wide counts and value distributions over one annotation file. Distributions for
    closed vocabularies (activity type, role type, result type, temporal type, recurrence
    pattern, emotion, factuality, certainty) list every possible value in its data_type.py enum
    order, including ones that never occur (count 0), for a complete, stable picture rather than
    a sparse one that changes shape between reports.
    """
    rows = flatten_turns(conversations)  # [(chat_id, turn_num, utterance, outputs), ...]

    chat_ids = {c for c, _t, _u, _o in rows}
    total_turns = len(rows)
    annotated_turns = sum(1 for _c, _t, _u, outputs in rows if outputs)
    output_entries = sum(len(outputs) for _c, _t, _u, outputs in rows)

    human_names = set()
    annotators = set()
    for conv in conversations:
        for item in conv:
            if item.get("human"):
                human_names.add(item["human"])
            for entry in (item.get("Output") or []):
                if entry.get("annotator"):
                    annotators.add(entry["annotator"])

    seen_activities = set()
    activity_types = Counter()
    role_counts = Counter()
    role_type_counts = Counter()
    result_type_counts = Counter()
    time_resolved_count = 0
    temporal_type_counts = Counter()
    recurrence_counts = Counter()

    for chat_id, _turn, _utt, outputs in rows:
        for entry in outputs:
            act = entry.get("activity") or {}
            aid = act.get("activity_id")
            if aid is not None and act.get("value") is not None:
                key = (chat_id, aid)
                if key not in seen_activities:
                    seen_activities.add(key)
                    if act.get("type"):
                        activity_types[act["type"]] += 1

            for role in ROLE_FIELDS:
                values = entry.get(role) or []
                role_counts[role] += len(values)
                if role in ROLE_TYPE_ROLES:
                    for v in values:
                        if v.get("type"):
                            role_type_counts[v["type"]] += 1
                elif role == "result":
                    for v in values:
                        if v.get("type"):
                            result_type_counts[v["type"]] += 1

            for tr in (entry.get("time_resolved") or []):
                time_resolved_count += 1
                if tr.get("temporal_type"):
                    temporal_type_counts[tr["temporal_type"]] += 1
                if tr.get("recurrence_pattern"):
                    recurrence_counts[tr["recurrence_pattern"]] += 1

    persp = turn_perspectives(conversations)
    emotion_counts = Counter(p["emotion"] for p in persp.values() if p.get("emotion"))
    factuality_counts = Counter(p["factuality"] for p in persp.values() if p.get("factuality"))
    certainty_counts = Counter(p["certainty"] for p in persp.values() if p.get("certainty"))

    return {
        "overview": {
            "conversations": len(chat_ids),
            "turns": total_turns,
            "annotated_turns": annotated_turns,
            "output_entries": output_entries,
            "unique_activities": len(seen_activities),
            "patients": len(human_names),
            "annotators": len(annotators),
            "time_expressions": role_counts["time"],
            "time_expressions_resolved": time_resolved_count,
        },
        "activity_types": activity_types,
        "roles": role_counts,
        "role_types": role_type_counts,
        "result_types": result_type_counts,
        "temporal_types": temporal_type_counts,
        "recurrence_patterns": recurrence_counts,
        "emotion": emotion_counts,
        "factuality": factuality_counts,
        "certainty": certainty_counts,
    }


# ═══ Report output: JSON + LaTeX ═══════════════════════════════════════════════

def overview_table_tex(stats):
    ov = stats["overview"]
    rows = "\n".join(f"{esc_tex(label)} & {value} \\\\" for label, value in [
        ("Conversations", ov["conversations"]),
        ("Turns", ov["turns"]),
        ("Annotated turns", ov["annotated_turns"]),
        ("Output entries", ov["output_entries"]),
        ("Unique activities", ov["unique_activities"]),
        ("Patients", ov["patients"]),
        ("Annotators", ov["annotators"]),
        ("Time expressions", ov["time_expressions"]),
        ("Time expressions resolved", ov["time_expressions_resolved"]),
    ])
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lr}\n\\toprule\n"
        "Statistic & Count \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        "\\caption{Corpus overview}\n"
        "\\label{tab:overview}\n"
        "\\end{table}\n"
    )


def distribution_table_tex(items, caption, label, header="Value"):
    """items: [(name, count), ...] in the order to display. Share is count / sum(all counts)."""
    total = sum(count for _name, count in items)
    rows = "\n".join(
        f"{esc_tex(name)} & {count} & {fmt_tex(count / total if total else None)} \\\\"
        for name, count in items
    )
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lrr}\n\\toprule\n"
        f"{header} & Count & Share \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        f"\\caption{{{esc_tex(caption)}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{table}\n"
    )


def write_outputs(stats, tex_sections, json_path, tex_path):
    with open(json_path, "w") as f:
        json.dump({k: (dict(v) if isinstance(v, Counter) else v) for k, v in stats.items()}, f, indent=2)
    with open(tex_path, "w") as f:
        f.write("% Auto-generated by annotation_statistics.py -- do not edit by hand.\n\n")
        f.write("\n".join(tex_sections))
    print(f"Wrote {json_path}")
    print(f"Wrote {tex_path}")


# ═══ CLI ═══════════════════════════════════════════════════════════════════════

def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute descriptive statistics for a manually annotated SRL conversation file."
    )
    parser.add_argument("--input", "-i", default="../../data/annotations_piek.json",
                         help="Path to the annotation JSON file (default: ../../data/annotations_piek.json).")
    parser.add_argument("--output", "-o", default=".",
                         help="Output folder for the report files (default: current directory); created if it "
                              "doesn't exist. Files are named after the input file: <stem>_statistics.json / .tex.")
    return parser.parse_args()


def main():
    args = parse_args()
    conversations = load_conversations(args.input)
    os.makedirs(args.output, exist_ok=True)

    stats = compute_statistics(conversations)

    tex_sections = [
        overview_table_tex(stats),
        distribution_table_tex(
            [(t.value, stats["activity_types"][t.value]) for t in data_type.ActivityType],
            "Activity types (unique activities)", "tab:activity-types", header="Activity type"),
        distribution_table_tex(
            [(role, stats["roles"][role]) for role in ROLE_FIELDS],
            "Semantic role fillers (annotation count per role)", "tab:role-counts", header="Role"),
        distribution_table_tex(
            [(t.value, stats["role_types"][t.value]) for t in data_type.RoleType],
            "Role filler types (agent/patient/agent\\_patient/experiencer/participant/qualification/instrument/location)",
            "tab:role-types", header="Type"),
        distribution_table_tex(
            [(t.value, stats["result_types"][t.value]) for t in data_type.ResultType],
            "Result types", "tab:result-types", header="Type"),
        distribution_table_tex(
            [(t.value, stats["temporal_types"][t.value]) for t in data_type.TemporalType],
            "Temporal types (resolved time expressions)", "tab:temporal-types", header="Temporal type"),
        distribution_table_tex(
            [(t.value, stats["recurrence_patterns"][t.value]) for t in data_type.RecurrencePattern],
            "Recurrence patterns", "tab:recurrence-patterns", header="Pattern"),
        distribution_table_tex(
            [(t.value, stats["emotion"][t.value]) for t in data_type.EmotionLabel],
            "Speaker emotion (per turn)", "tab:emotion", header="Emotion"),
        distribution_table_tex(
            [(t.value, stats["factuality"][t.value]) for t in data_type.Factuality],
            "Speaker factuality (per turn)", "tab:factuality", header="Factuality"),
        distribution_table_tex(
            [(t.value, stats["certainty"][t.value]) for t in data_type.Certainty],
            "Speaker certainty (per turn)", "tab:certainty", header="Certainty"),
    ]

    stem = os.path.splitext(os.path.basename(args.input))[0]
    json_path = os.path.join(args.output, f"{stem}_statistics.json")
    tex_path = os.path.join(args.output, f"{stem}_statistics.tex")
    write_outputs(stats, tex_sections, json_path, tex_path)


if __name__ == "__main__":
    main()
