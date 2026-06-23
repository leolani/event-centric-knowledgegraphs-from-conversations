"""
Classify agent/patient/instrument/location values in event_srl_time_resolved.json.zip
using OpenAI, then write events_srl_typed.json with typed role entries.

Usage:
    export OPENAI_API_KEY=sk-...
    python src/classify_roles.py
"""

import json
import os
import zipfile
from pathlib import Path

from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
ROLES       = ["agent", "patient", "instrument", "location"]
BATCH_SIZE  = 50          # values per API call
MODEL       = "gpt-4o-mini"
CACHE_FILE  = Path("data/role_type_cache.json")
INPUT_ZIP   = Path("data/event_srl_time_resolved.json.zip")
OUTPUT_FILE = Path("data/events_srl_typed.json")

SYSTEM_PROMPT = """\
You are an entity-type classifier for a health-dialogue dataset about diabetes management.

Given a JSON list of text spans that appear as semantic role fillers (agent, patient,
instrument, or location), return a JSON object mapping each span to its entity type.

Use exactly one of these types:
  person        – named or referred person (patient, caregiver, assistant)
  food          – any food, drink, ingredient, or meal
  medication    – drug, supplement, insulin, pill
  device        – physical tool or medical device (glucometer, pump, bike)
  body_part     – body part or physiological measure (blood sugar, HbA1c)
  location      – place, setting, or environment
  activity      – an action or exercise named as a filler
  quantity      – amount, dose, duration expressed as a filler
  concept       – abstract health/lifestyle concept
  other         – anything that does not fit above

Return ONLY valid JSON: {"span": "type", ...}
No explanation, no markdown fences."""

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


def classify_batch(client: OpenAI, values: list[str]) -> dict[str, str]:
    """Send a batch of values to OpenAI and return span→type mapping."""
    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": json.dumps(values)},
        ],
    )
    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if model adds them despite instructions
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def classify_all(client: OpenAI, unique_values: list[str]) -> dict[str, str]:
    cache = load_cache()
    to_classify = [v for v in unique_values if v not in cache]
    total = len(to_classify)
    print(f"Values to classify: {total}  (cached: {len(unique_values) - total})")

    for i in range(0, total, BATCH_SIZE):
        batch = to_classify[i : i + BATCH_SIZE]
        print(f"  Batch {i // BATCH_SIZE + 1}/{-(-total // BATCH_SIZE)}  ({i}–{i+len(batch)-1})", end="", flush=True)
        try:
            result = classify_batch(client, batch)
            # Fill any values the model silently dropped
            for v in batch:
                cache[v] = result.get(v, "other")
            save_cache(cache)
            print(f"  OK")
        except Exception as exc:
            print(f"  ERROR: {exc}")
            for v in batch:
                cache.setdefault(v, "other")
            save_cache(cache)

    return cache


def type_role_list(values: list, cache: dict) -> list[dict]:
    """Convert a plain list of strings to [{value, type}] dicts."""
    out = []
    for v in (values or []):
        if v:
            out.append({"value": v, "type": cache.get(v, "other")})
    return out


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)

    # Load data
    print(f"Loading {INPUT_ZIP} …")
    with zipfile.ZipFile(INPUT_ZIP) as z:
        inner = [n for n in z.namelist() if n.endswith(".json")][0]
        with z.open(inner) as f:
            data = json.load(f)

    # Collect unique role values
    unique_values: set[str] = set()
    for turn_list in data:
        for turn in turn_list:
            for output in turn.get("Output", []):
                for role in ROLES:
                    for v in (output.get(role) or []):
                        if v:
                            unique_values.add(v)

    print(f"Unique role values: {len(unique_values)}")

    # Classify
    cache = classify_all(client, sorted(unique_values))

    # Build typed output
    print("Building typed output …")
    typed_data = []
    for turn_list in data:
        typed_turn_list = []
        for turn in turn_list:
            typed_turn = dict(turn)
            typed_outputs = []
            for output in turn.get("Output", []):
                typed_output = dict(output)
                for role in ROLES:
                    typed_output[role] = type_role_list(output.get(role) or [], cache)
                typed_outputs.append(typed_output)
            typed_turn["Output"] = typed_outputs
            typed_turn_list.append(typed_turn)
        typed_data.append(typed_turn_list)

    OUTPUT_FILE.write_text(json.dumps(typed_data, indent=2, ensure_ascii=False))
    print(f"Saved → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
