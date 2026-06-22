"""
Reads event_srl.json.zip, calls OpenAI to resolve relative time expressions
to absolute dates relative to each conversation's date, and writes the
enriched data to data/event_srl_time_resolved.json.
"""

import json
import os
import zipfile
from typing import Literal, Optional

from openai import OpenAI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------

def _load_key() -> str:
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env
    key_path =  "../../../keys/openaikey1.txt"
    with open(key_path) as fh:
        return fh.read().strip()


client = OpenAI(api_key=_load_key())

# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

class ResolvedTime(BaseModel):
    time_expression: str = Field(description="The original time expression from the utterance.")
    temporal_type: Literal["point", "range", "recurring", "vague"] = Field(
        description=(
            "point: a single specific date; "
            "range: a span with a start and end; "
            "recurring: a repeating pattern (daily, weekly, …); "
            "vague: too ambiguous to assign a date."
        )
    )
    absolute_date: Optional[str] = Field(
        default=None,
        description="ISO-8601 date (YYYY-MM-DD) for a point-type expression, otherwise null."
    )
    date_range_start: Optional[str] = Field(
        default=None,
        description="ISO-8601 start date for a range-type expression, otherwise null."
    )
    date_range_end: Optional[str] = Field(
        default=None,
        description="ISO-8601 end date for a range-type expression, otherwise null."
    )
    recurrence_pattern: Optional[str] = Field(
        default=None,
        description="Human-readable recurrence description for recurring-type expressions (e.g. 'every day', 'twice a week'), otherwise null."
    )
    probability: float = Field(
        ge=0.0, le=1.0,
        description=(
            "Confidence that the resolved date/range/pattern is correct, from 0.0 (no idea) to 1.0 (certain). "
            "Reflect genuine uncertainty: vague expressions get low scores, precise ones get high scores."
        )
    )
    reasoning: str = Field(
        description="One-sentence explanation of how the expression was resolved."
    )


class ResolvedTimeList(BaseModel):
    resolutions: list[ResolvedTime]


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a temporal-expression resolver for medical conversations.

You will receive:
  - conversation_date: the date the conversation took place (YYYY-MM-DD)
  - utterance: the sentence containing the time expression
  - time_expressions: a list of time expressions extracted from the utterance

For EACH time expression, resolve it to an absolute date (or date range, or
recurrence pattern) relative to the conversation_date.

Rules:
- "yesterday" → the day before conversation_date
- "lately", "recently", "these past few days" → a range ending on conversation_date,
  typically spanning 3–14 days back (use your best judgment)
- "last week" → the 7-day period ending on conversation_date
- "daily", "every day" → recurring pattern, no absolute date
- "twice a week" → recurring pattern
- "after dinner" → recurring pattern anchored to the dinner meal
- "this morning" → conversation_date itself
- "today" → conversation_date
- Expressions that cannot be resolved to any date → temporal_type "vague"

Always return exactly one ResolvedTime object per time expression, in the same
order as the input list.
"""

# ---------------------------------------------------------------------------
# Resolution logic
# ---------------------------------------------------------------------------

def resolve_time_expressions(
    conversation_date: str,
    utterance: str,
    time_expressions: list[str],
) -> list[ResolvedTime]:
    """
    Calls OpenAI to resolve a list of time expressions from a single utterance.
    Returns one ResolvedTime per expression (same order).
    """
    user_content = json.dumps({
        "conversation_date": conversation_date,
        "utterance": utterance,
        "time_expressions": time_expressions,
    }, ensure_ascii=False)

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=ResolvedTimeList,
        temperature=0,
    )

    return response.choices[0].message.parsed.resolutions


# ---------------------------------------------------------------------------
# Date parsing helper
# ---------------------------------------------------------------------------

def parse_conversation_date(raw: str) -> str:
    """Convert '2013,Apr,13' to '2013-04-13'."""
    from datetime import datetime
    try:
        return datetime.strptime(raw.strip(), "%Y,%b,%d").strftime("%Y-%m-%d")
    except ValueError:
        return raw  # return as-is if format is unexpected


# ---------------------------------------------------------------------------
# Cache to avoid duplicate API calls for same (date, expression, utterance)
# ---------------------------------------------------------------------------

def build_cache_key(date: str, utterance: str, expr: str) -> tuple:
    return (date, utterance, expr)


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def process(input_zip: str, output_json: str) -> None:
    # Load data
    with zipfile.ZipFile(input_zip) as zf:
        names = [n for n in zf.namelist() if n.endswith(".json")]
        with zf.open(names[0]) as fh:
            data = json.load(fh)

    # Build a de-duplicated work list: (iso_date, utterance) → [expressions]
    # We cache results per (iso_date, utterance, expression).
    cache: dict[tuple, ResolvedTime] = {}

    # Count totals for progress reporting
    total_calls = 0
    for chat_turns in data:
        for turn in (chat_turns if isinstance(chat_turns, list) else [chat_turns]):
            outputs = turn.get("Output") or []
            utterance = turn.get("Input", {}).get("utterance", "")
            raw_date = turn.get("date", "")
            iso_date = parse_conversation_date(raw_date)
            for output in outputs:
                times = [t for t in (output.get("time") or []) if t.strip()]
                if times:
                    total_calls += 1

    print(f"Utterances with time expressions: {total_calls}")

    # Process
    processed = 0
    enriched_data = []

    for chat_turns in data:
        enriched_turns = []
        for turn in (chat_turns if isinstance(chat_turns, list) else [chat_turns]):
            raw_date = turn.get("date", "")
            iso_date = parse_conversation_date(raw_date)
            utterance = turn.get("Input", {}).get("utterance", "")
            outputs = turn.get("Output") or []

            enriched_outputs = []
            for output in outputs:
                times = [t for t in (output.get("time") or []) if t.strip()]

                if not times:
                    enriched_outputs.append(output)
                    continue

                # Find which expressions we still need to resolve
                new_exprs = [
                    t for t in times
                    if build_cache_key(iso_date, utterance, t) not in cache
                ]

                if new_exprs:
                    processed += 1
                    if processed % 50 == 0 or processed == 1:
                        print(f"  API call {processed}/{total_calls} …")
                    try:
                        resolutions = resolve_time_expressions(iso_date, utterance, new_exprs)
                        for expr, resolved in zip(new_exprs, resolutions):
                            cache[build_cache_key(iso_date, utterance, expr)] = resolved
                    except Exception as exc:
                        print(f"  ERROR resolving {new_exprs} in '{utterance[:60]}': {exc}")
                        for expr in new_exprs:
                            cache[build_cache_key(iso_date, utterance, expr)] = ResolvedTime(
                                time_expression=expr,
                                temporal_type="vague",
                                probability=0.0,
                                reasoning=f"Resolution failed: {exc}",
                            )

                # Attach resolved times to output
                time_resolved = [
                    cache[build_cache_key(iso_date, utterance, t)].model_dump()
                    for t in times
                ]
                enriched_output = dict(output)
                enriched_output["time_resolved"] = time_resolved
                enriched_outputs.append(enriched_output)

            enriched_turn = dict(turn)
            enriched_turn["Output"] = enriched_outputs
            enriched_turns.append(enriched_turn)

        enriched_data.append(enriched_turns)

    # Write output
    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as fh:
        json.dump(enriched_data, fh, indent=2, ensure_ascii=False)

    print(f"\nDone. Enriched data written to {output_json}")
    print(f"Cache size (unique resolutions): {len(cache)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[2]
    input_zip = str(repo_root / "data" / "event_srl.json.zip")
    output_json = str(repo_root / "data" / "event_srl_time_resolved.json")

    print(f"Input : {input_zip}")
    print(f"Output: {output_json}")
    process(input_zip, output_json)
