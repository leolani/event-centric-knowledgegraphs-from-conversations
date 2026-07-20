# SRL Evaluation

`evaluate.py` scores the LLM-generated SRL output against the manually annotated gold
standard: how well does the automatic pipeline (`llm_event_extraction.py`) find the same
activities, semantic roles, and types a human annotator did with `annotation_tool.html`?

## Requirements

Run from `src/cltl` with the project's virtual environment (see the top-level `README.md` for
setup). No extra dependencies beyond the standard library.

## Input files

Both `--gold` and `--system` point at files with the same shape: a list of conversations, each
a list of turn entries:

```json
{ "chat": 0, "date": "...", "human": "Jan", "Input": {"turn": 1, "speaker": "...", "utterance": "..."},
  "Output": [ { "activity": {...}, "agent": [...], "patient": [...], "agent_patient": [...],
                "experiencer": [...], "instrument": [...], "location": [...], "result": [...],
                "time": [...], "perspective": {...} } ] }
```

- **Gold** (default `annotation/annotations.json`): exported from `annotation_tool.html` —
  see `readme-annotation.md`.
- **System** (default `../../data/event_srl.json`): produced by `llm_event_extraction.py`.

Every evaluation command restricts itself to chats **present in gold**: a chat gold hasn't been
annotated yet is ignored entirely, rather than counting every system prediction there as a
false positive. `--human` isn't a flag — the patient's name is read from each chat's own
`"human"` field, used to recognize a value like `"Jan"` as a speaker reference alongside
pronouns (see [Mismatch log](#mismatch-log-mismatches)).

## Quick start

```bash
python evaluate.py all --output ../../data
```

Runs everything (SRL strict + lenient, BLANC strict + lenient, type accuracy, n-gram, and the
mismatch log) with the default gold/system paths, writing `evaluation_all.json`,
`evaluation_all.tex`, and `evaluation_all_mismatches.log` into `../../data`.

## CLI options

```
python evaluate.py {srl,blanc,types,ngram,mismatches,all} [--gold PATH] [--system PATH] [--output DIR] [subcommand options]
```

`--gold`, `--system`, and `--output` must come **after** the subcommand, not before (an
argparse quirk with subparsers — see the comment above `parse_args()` in the code).

| Flag | Applies to | Default | Meaning |
|---|---|---|---|
| `--gold` | all | `annotation/annotations.json` | Gold-standard JSON file. |
| `--system` | all | `../../data/event_srl.json` | System (LLM) output JSON file. |
| `--output` | all | `.` (current directory) | Output folder, created if missing. |
| `--mode` | `srl`, `blanc` | `both` | `strict`, `lenient`, or `both`. |
| `--threshold` | `ngram` | `0.5` | Minimum n-gram overlap (Dice coefficient, 0–1) to count as a match. |
| `--ngram-size` | `ngram` | `3` | Character n-gram size. |

Output files use default names per subcommand: `evaluation_<command>.json`,
`evaluation_<command>.tex`, and (for `mismatches`/`all`) `evaluation_mismatches.log` /
`evaluation_all_mismatches.log`. `mismatches` writes only the log, no JSON/TEX.

Examples:

```bash
# Lenient-only SRL scoring with explicit paths
python evaluate.py srl --mode lenient --gold annotation/annotations.json --system ../../data/event_srl.json --output ../../data

# Just the side-by-side mismatch log
python evaluate.py mismatches --output ../../data

# Chat-level n-gram scoring with a looser threshold
python evaluate.py ngram --threshold 0.3 --output ../../data
```

## Methods

### Turn/entry alignment

Gold and system `Output` entries are compared per `(chat, turn)`. Within a turn, entries are
paired up by their **activity span**: a bare reference entry (one that only carries an
`activity_id`, no `value`/`offset` of its own) resolves its span through the entry that first
introduced that `activity_id` in the conversation. Pairing uses a greedy, best-overlap-first
bipartite match (`greedy_match`), under one of two offset criteria:

- **strict**: gold and system spans must be exactly equal (same offset and length).
- **lenient**: gold and system spans only need to overlap.

This alignment underlies every offset-based command below (`srl`, `blanc`, `types`).

### SRL scoring (`srl`)

Precision/recall/F1 for the activity span and each semantic role
(`agent`/`patient`/`agent_patient`/`experiencer`/`instrument`/`location`/`result`/`time`),
strict or lenient. Roles are scored *within* each matched entry pair; an entry with no
counterpart in the other side contributes all its role spans as false negatives (gold-only) or
false positives (system-only).

In **lenient** mode only, an extra **`participant`** row pools `agent`, `patient`,
`agent_patient`, and `experiencer` together and asks a coarser question: was the participant
span found at all, regardless of which of those four specific roles gold and system each
assigned it to? Matching is two-pass (`match_participant_roles`): same-role pairs first, then
whatever's left over is pooled across all four roles and matched again by span overlap alone —
a gold `agent_patient` and a system `patient` with overlapping spans count as one participant
match rather than one false negative plus one false positive. `participant` is a supplementary,
alternative view of spans already counted in the per-role rows above, so it is **excluded**
from the `overall` row (including it would double-count those spans).

Example (real chat-0 run, lenient mode):

```
Category       & TP & FP & FN & Precision & Recall & F1
activity       &  4 &  6 &  4 &     0.400 &  0.500 & 0.444
agent_patient  &  0 &  8 &  2 &     0.000 &  0.000 & 0.000
time           &  3 &  5 &  1 &     0.375 &  0.750 & 0.500
participant    &  0 &  9 &  2 &     0.000 &  0.000 & 0.000
overall        &  8 & 22 & 11 &     0.267 &  0.421 & 0.327
```

### Activity coreference (`blanc`)

BLANC (Recasens & Hovy, 2011): does the system group turn mentions of the same real-world
activity under one `activity_id` the same way gold does? Turn mentions are aligned per chat via
the same entry-matching used for SRL; two aligned mentions are "coreferent" in gold (or system)
if their respective entries share the same `activity_id`. BLANC is the average of the
coreference-link F1 and the non-coreference-link F1 across all pairs of aligned mentions in a
chat, reported per chat plus an aggregate `overall` row.

### Type accuracy (`types`)

For every span that **leniently** matches between gold and system — activity plus every typed
role except `time` (which has no type) — is the assigned type also correct (e.g. both say
`exercise`, not one `exercise` and one `treatment`)? Reuses the lenient SRL alignment.

### Chat-level n-gram matching (`ngram`)

The three commands above all anchor matching to a specific turn and offset. `ngram` instead
asks a coarser, **offset-free** question per **chat**: character by character, did the system
find the same activities and role fillers anywhere in the conversation, regardless of exactly
which turn or span they were assigned to?

Two expressions are compared by their **character n-gram overlap** — a Dice coefficient over
character trigrams by default (`ngram_overlap`; tune size with `--ngram-size`), treating
n-grams as multisets so repeated substrings count more than once. Two items are considered a
match if this overlap is `>= --threshold` (default 0.5), aligned greedily, best-score-first
(`greedy_match_ngram`).

- **Activities** are matched as coreference chains, not individual mentions, but *without*
  concatenating a chain into one blob first: every expression sharing an `activity_id` is one
  mention of that chain (`activity_mentions_by_chat`), and a gold chain matches a system chain
  if their single **best mention pairing** clears the threshold (`best_mention_overlap`) — the
  chain gets credit if at least one phrasing lines up, whatever the rest of its mentions look
  like. (An earlier version concatenated every mention of a chain into one long string before
  comparing; that diluted the score below threshold whenever a chain had several differently
  worded mentions or the two chains differed greatly in length, even when a mention matched
  exactly — best-mention matching avoids that.)
- **Roles** are matched value-by-value, pooling every individual value anywhere in the chat
  (`pool_role_values_by_chat`) — an individual role filler has no coreference identity the way
  an activity does, so there's no chain to take the best mention of.

Reports one table per chat, plus an `"average"` entry/table: the unweighted (macro) mean of
every metric across chats.

Example (real chat-0 run, default threshold/size):

```
Category       & TP & FP & FN & Precision & Recall & F1
activity       &  2 &  1 &  3 &     0.667 &  0.400 & 0.500
agent_patient  &  1 &  7 &  1 &     0.125 &  0.500 & 0.200
time           &  3 &  5 &  1 &     0.375 &  0.750 & 0.500
overall        &  7 & 16 &  9 &     0.304 &  0.438 & 0.359
```

`ngram` and `srl` are complementary, not interchangeable: `srl` rewards getting the *exact
turn and span* right; `ngram` rewards finding the *content* anywhere in the chat. A gap between
the two for a given category is itself informative — e.g. a much lower `ngram` activity score
than `srl`'s usually means the system's coreference linking is fragmenting one real activity
chain into several `activity_id`s (see `blanc`), while a much lower `srl` score than `ngram`'s
usually means the content is right but attributed to the wrong turn or span.

### Mismatch log (`mismatches`)

A side-by-side, human-readable log of every gold-only (false negative) and system-only (false
positive) item, under **lenient** matching only — everything `srl --mode lenient` would count
as FN/FP, but as full records grouped by turn instead of a tally, for inspection.

Each system-only record is flagged where applicable:

- **`[HALLUCINATION]`** — the value doesn't occur anywhere in the turn's utterance at all.
  Usually the model confused this turn with a different one. The log header reports a
  **hallucination score** = hallucinations / total turns evaluated.
- **`[SPEAKER MATCH]`** — the value refers to a conversation participant (a first/second-person
  pronoun, *or* the patient's own name from the `"human"` field — e.g. gold says `"Jan"`,
  system says `"you"`) in a person role, **and** gold independently makes its own speaker
  reference for that same role in that turn — just not via the exact span or kind of
  expression gold chose.
- **`[PARTICIPANT MATCH]`** — gold and system found the same participant span but filed it
  under different roles among `agent`/`patient`/`agent_patient`/`experiencer` (e.g. gold said
  `agent_patient`, system said `patient`). Category is shown as `gold_role/sys_role`.

Example:

```
# 9 HALLUCINATION(s): system value not found anywhere in the turn's utterance
# 1 SPEAKER MATCH(es): system value refers to a speaker (a pronoun or the
#   patient's own name) for a role where gold ALSO makes a speaker reference (pronoun or
#   name, not necessarily the same kind), just not aligned with the specific span gold chose
# 0 PARTICIPANT MATCH(es): gold and system found the same participant span but
#   filed it under different roles among agent/patient/agent_patient/experiencer
# Hallucination score: 9/9 = 1.000

chat 0 turn 3: "Physical activity, like cycling, is crucial in managing your diabetes. ..."
  activity       GOLD: 'cycling' [24:31] type=exercise               | SYSTEM: --
  activity       GOLD: --                                            | SYSTEM: 'been out' [43:51] type=exercise [HALLUCINATION]
  result         GOLD: 'crucial in managing your diabetes' [36:69] type=impact | SYSTEM: --
```

## Results (output files)

### JSON

`evaluation_<command>.json` holds one key per report:

| Command | JSON keys |
|---|---|
| `srl` | `srl_strict`, `srl_lenient` (each `{category: {tp, fp, fn, precision, recall, f1}, ..., "overall": ...}`; `srl_lenient` also has `"participant"`) |
| `blanc` | `blanc_strict`, `blanc_lenient` (each `{chat_id: {blanc, precision_c, recall_c, f1_c, precision_n, recall_n, f1_n, rc, ck, cg, rn, nk, ng, mentions}, ..., "overall": ...}`) |
| `types` | `types` (`{category: {correct, total, accuracy}, ..., "overall": ...}`) |
| `ngram` | `ngram` (`{chat_id: {category: {tp, fp, fn, precision, recall, f1}, ..., "overall": ...}, ..., "average": {...}}`) |
| `all` | all of the above, plus a separate `evaluation_all_mismatches.log` |

`mismatches` writes no JSON — only the `.log` file.

### LaTeX

`evaluation_<command>.tex` contains one `\begin{table}...\end{table}` per report section (e.g.
`all` produces two SRL tables, two BLANC tables, one type-accuracy table, and one n-gram table
per chat plus one average — see the examples above). Underscores in category/role names (e.g.
`agent_patient`) are escaped for LaTeX. `\include` or copy-paste the tables directly into a
paper or report.

### Mismatch log

`evaluation_mismatches.log` / `evaluation_all_mismatches.log` is a plain-text file, grouped by
`chat N turn M: "utterance"`, with one line per mismatch showing gold and system side by side
(see the [Mismatch log](#mismatch-log-mismatches) example above). Not machine-readable JSON —
intended for a human to scan and spot systematic error patterns.
