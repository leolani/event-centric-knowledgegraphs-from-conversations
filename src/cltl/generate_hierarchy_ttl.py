"""Generate a TTL hierarchy from activity_type_counts, role_type_counts, and temporal_type_counts."""

import csv
from pathlib import Path


def to_camel(s: str) -> str:
    return "".join(w.capitalize() for w in s.replace("_", " ").split())


def to_label(s: str) -> str:
    return s.replace("_", " ").title()


def load_activity_types():
    with open("data/activity_type_counts.csv") as f:
        return [(r["activity_type"], int(r["count"])) for r in csv.DictReader(f)]


def load_role_types():
    with open("data/role_type_counts_summary.csv") as f:
        reader = csv.DictReader(f)
        roles = reader.fieldnames[1:]
        totals = {}
        for row in reader:
            totals[row["type"]] = sum(int(row[r]) for r in roles)
    return sorted(totals.items(), key=lambda x: -x[1])


def load_temporal_types():
    with open("data/temporal_type_counts.csv") as f:
        return [(r["temporal_type"], int(r["count"])) for r in csv.DictReader(f)]


def write_ttl(path: str):
    activity_types = load_activity_types()
    role_types     = load_role_types()
    temporal_types = load_temporal_types()

    lines = []

    # ── Prefixes ──────────────────────────────────────────────────────────────
    lines += [
        "@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
        "@prefix owl:  <http://www.w3.org/2002/07/owl#> .",
        "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
        "@prefix eckg: <https://cltl.nl/eckg/> .",
        "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
        "",
        "# ── Ontology declaration ─────────────────────────────────────────────",
        "<https://cltl.nl/eckg/> a owl:Ontology ;",
        '    rdfs:label "Event-Centric Knowledge Graph Taxonomy" ;',
        '    rdfs:comment "Hierarchy of activity types, entity role types, and temporal types extracted from diabetes dialogue annotations." .',
        "",
    ]

    # ── Top-level classes ─────────────────────────────────────────────────────
    lines += [
        "# ── Top-level classes ────────────────────────────────────────────────",
        "eckg:EventConcept a owl:Class ;",
        '    rdfs:label "Event Concept" ;',
        '    rdfs:comment "Root class for all typed concepts in the event-centric KG." .',
        "",
        "eckg:ActivityType a owl:Class ;",
        "    rdfs:subClassOf eckg:EventConcept ;",
        '    rdfs:label "Activity Type" .',
        "",
        "eckg:EntityType a owl:Class ;",
        "    rdfs:subClassOf eckg:EventConcept ;",
        '    rdfs:label "Entity Type" .',
        "",
        "eckg:TemporalType a owl:Class ;",
        "    rdfs:subClassOf eckg:EventConcept ;",
        '    rdfs:label "Temporal Type" .',
        "",
    ]

    # ── Activity types ────────────────────────────────────────────────────────
    lines.append("# ── Activity types ───────────────────────────────────────────────────")
    for name, count in activity_types:
        uri = f"eckg:ActivityType_{to_camel(name)}"
        lines += [
            f"{uri} a owl:Class ;",
            f"    rdfs:subClassOf eckg:ActivityType ;",
            f'    rdfs:label "{to_label(name)}" ;',
            f"    skos:notation {count} ;",
            f'    rdfs:comment "Frequency count: {count}" .',
            "",
        ]

    # ── Entity / role types ───────────────────────────────────────────────────
    lines.append("# ── Entity role types (summed across agent/patient/instrument/location) ──")
    for name, count in role_types:
        uri = f"eckg:EntityType_{to_camel(name)}"
        lines += [
            f"{uri} a owl:Class ;",
            f"    rdfs:subClassOf eckg:EntityType ;",
            f'    rdfs:label "{to_label(name)}" ;',
            f"    skos:notation {count} ;",
            f'    rdfs:comment "Frequency count: {count}" .',
            "",
        ]

    # ── Temporal types ────────────────────────────────────────────────────────
    lines.append("# ── Temporal types ───────────────────────────────────────────────────")
    for name, count in temporal_types:
        uri = f"eckg:TemporalType_{to_camel(name)}"
        lines += [
            f"{uri} a owl:Class ;",
            f"    rdfs:subClassOf eckg:TemporalType ;",
            f'    rdfs:label "{to_label(name)}" ;',
            f"    skos:notation {count} ;",
            f'    rdfs:comment "Frequency count: {count}" .',
            "",
        ]

    Path(path).write_text("\n".join(lines))
    print(f"Saved → {path}")
    print(f"  {len(activity_types)} activity types")
    print(f"  {len(role_types)} entity/role types")
    print(f"  {len(temporal_types)} temporal types")


if __name__ == "__main__":
    write_ttl("data/eckg_hierarchy.ttl")
