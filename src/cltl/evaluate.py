"""
Evaluate LLM-generated SRL annotations (default: ../../data/event_srl.json, produced by
llm_event_extraction.py) against the manually annotated gold standard (default:
annotation/annotations.json, exported from annotation_tool.html).

Both files share the same shape: a list of conversations, each a list of
{chat, date, human, Input, Output} turn entries, where Output is a list of annotation
entries (perspective, activity, agent, patient, agent_patient, experiencer, instrument,
location, result, time, time_resolved) — see data_type.py for the field values.

Gold and system entries are matched by (chat, Input.turn); within a turn, entries are
aligned to each other via their activity span (or, for a bare reference entry with no
span of its own, via the span of the entry that first introduced its activity_id). Only
chats present in gold are evaluated -- system chats gold doesn't cover are ignored entirely.

Usage:
    python evaluate.py srl [--mode strict|lenient|both]
    python evaluate.py blanc [--mode strict|lenient|both]
    python evaluate.py types
    python evaluate.py ngram [--threshold 0.5] [--ngram-size 3]
    python evaluate.py mismatches
    python evaluate.py all
"""

import argparse
import json
import os
from collections import Counter, defaultdict

ROLE_FIELDS = ["agent", "patient", "agent_patient", "experiencer", "instrument", "location", "result", "time"]
# Fields that carry a "type" value worth scoring; "time" spans have no type.
TYPED_FIELDS = ["activity"] + [r for r in ROLE_FIELDS if r != "time"]

# The four roles that all identify the participant undergoing a change or experiencing a
# state (as opposed to instrument/location/result/time). Gold and system frequently agree on
# WHICH span is the participant but disagree on which of these four roles it falls under
# (e.g. gold calls it agent_patient, system calls it patient) -- grouping them lets a lenient
# "participant" metric and the mismatch log recognize that as a role mismatch, not a full miss.
PARTICIPANT_ROLES = {"agent", "patient", "agent_patient", "experiencer"}
PARTICIPANT_ROLE_ORDER = [r for r in ROLE_FIELDS if r in PARTICIPANT_ROLES]


# ═══ Loading ══════════════════════════════════════════════════════════════════

def load_conversations(path):
    with open(path) as f:
        return json.load(f)


def flatten_turns(conversations):
    """[(chat_id, turn_num, utterance, Output_list), ...], sorted by (chat_id, turn_num)."""
    rows = []
    for conv in conversations:
        for item in conv:
            rows.append((item["chat"], item["Input"]["turn"], item["Input"]["utterance"], item.get("Output") or []))
    rows.sort(key=lambda r: (r[0], r[1]))
    return rows


def filter_to_gold_chats(sys_conversations, gold_conversations):
    """Drop every system entry whose chat_id doesn't appear anywhere in gold. Evaluation is
    restricted to chats gold actually covers -- a chat gold hasn't been annotated for yet is
    ignored entirely, rather than counting every system prediction there as a false positive."""
    gold_chat_ids = {chat_id for chat_id, _t, _u, _o in flatten_turns(gold_conversations)}
    return [[item for item in conv if item.get("chat") in gold_chat_ids] for conv in sys_conversations]


def build_human_by_chat(conversations):
    """chat_id -> the patient's name (the "human" field), used to recognize a value like
    "Jan" as also referring to a speaker, alongside pronouns."""
    names = {}
    for conv in conversations:
        for item in conv:
            if item.get("human") and item["chat"] not in names:
                names[item["chat"]] = item["human"]
    return names


def build_origin_lookups(conversations):
    """(chat_id, activity_id) -> {offset, length, type} of the entry that FIRST introduced
    that activity_id with its own value/offset/length, in turn order. A bare reference entry
    (no value of its own) resolves its activity's span/type through this map."""
    origins = {}
    for chat_id, _turn, _utt, outputs in flatten_turns(conversations):
        for entry in outputs:
            act = entry.get("activity") or {}
            aid = act.get("activity_id")
            if aid is None:
                continue
            key = (chat_id, aid)
            if key not in origins and act.get("value") is not None and act.get("offset") is not None:
                origins[key] = {"offset": act["offset"], "length": act.get("length", len(act["value"])), "type": act.get("type")}
    return origins


def activity_anchor(entry, chat_id, origins):
    """(offset, length, type) used to align this entry's activity across gold/system, or
    None if it can't be resolved (e.g. a reference to an activity_id with no known origin)."""
    act = entry.get("activity") or {}
    if act.get("value") is not None and act.get("offset") is not None:
        return act["offset"], act.get("length", len(act["value"])), act.get("type")
    origin = origins.get((chat_id, act.get("activity_id")))
    return (origin["offset"], origin["length"], origin["type"]) if origin else None


# ═══ Span matching ════════════════════════════════════════════════════════════

def span_of(d):
    if d.get("offset") is None or d.get("length") is None:
        return None
    return d["offset"], d["length"]


def spans_exact(a, b):
    return a is not None and b is not None and a == b


def spans_overlap(a, b):
    if a is None or b is None:
        return False
    a_start, a_len = a
    b_start, b_len = b
    return a_start < b_start + b_len and b_start < a_start + a_len


def greedy_match(gold_items, sys_items, gold_span_fn, sys_span_fn, mode):
    """One-to-one alignment of gold_items to sys_items under a "strict" (exact span) or
    "lenient" (overlapping span) criterion. Greedy: each gold item takes the best available
    (highest-overlap, for lenient) unused system item that satisfies the criterion.
    Returns (matched_pairs, unmatched_gold, unmatched_sys); matched_pairs is
    [(gold_item, sys_item), ...]."""
    match_fn = spans_exact if mode == "strict" else spans_overlap
    remaining = list(enumerate(sys_items))
    matched = []
    unmatched_gold = []
    for g in gold_items:
        g_span = gold_span_fn(g)
        best_idx, best_item, best_overlap = None, None, -1
        for idx, s in remaining:
            s_span = sys_span_fn(s)
            if not match_fn(g_span, s_span):
                continue
            if mode == "lenient":
                overlap = min(g_span[0] + g_span[1], s_span[0] + s_span[1]) - max(g_span[0], s_span[0])
                if overlap > best_overlap:
                    best_overlap, best_idx, best_item = overlap, idx, s
            else:
                best_idx, best_item = idx, s
                break
        if best_item is not None:
            matched.append((g, best_item))
            remaining = [(i, s) for i, s in remaining if i != best_idx]
        else:
            unmatched_gold.append(g)
    unmatched_sys = [s for _, s in remaining]
    return matched, unmatched_gold, unmatched_sys


def _anchor_xy(entry, chat_id, origins):
    a = activity_anchor(entry, chat_id, origins)
    return (a[0], a[1]) if a else None


def match_entries_for_turn(gold_outputs, sys_outputs, chat_id, gold_origins, sys_origins, mode):
    """Align gold Output entries to system Output entries for one turn, via their activity span."""
    return greedy_match(
        gold_outputs, sys_outputs,
        lambda e: _anchor_xy(e, chat_id, gold_origins),
        lambda e: _anchor_xy(e, chat_id, sys_origins),
        mode,
    )


def match_role_spans(gold_entry, sys_entry, role, mode):
    gold_spans = [d for d in (gold_entry.get(role) or []) if span_of(d) is not None]
    sys_spans = [d for d in (sys_entry.get(role) or []) if span_of(d) is not None]
    return greedy_match(gold_spans, sys_spans, span_of, span_of, mode)


def match_participant_roles(gold_entry, sys_entry, mode):
    """Two-pass matching across the four participant roles (agent/patient/agent_patient/
    experiencer) for one matched (gold_entry, sys_entry) pair: first match within each role
    separately (same as match_role_spans), then pool whatever's left unmatched across all four
    roles and match again by span only, ignoring which specific role each item was filed
    under. A leftover gold item and leftover system item that overlap despite being filed
    under different roles are the SAME real participant, just labeled differently -- a role
    mismatch, not an independent miss on each side.

    Returns (same_role_matches, cross_role_matches, remaining_gold, remaining_sys):
    - same_role_matches: [(gold_span, sys_span), ...] matched within the same role.
    - cross_role_matches: [(gold_role, gold_span, sys_role, sys_span), ...].
    - remaining_gold / remaining_sys: [(role, span), ...] still unmatched after both passes --
      genuine misses with no role-mismatch explanation.
    """
    same_role_matches = []
    leftover_gold, leftover_sys = [], []
    for role in PARTICIPANT_ROLE_ORDER:
        role_matched, role_fn, role_fp = match_role_spans(gold_entry, sys_entry, role, mode)
        same_role_matches.extend(role_matched)
        leftover_gold.extend((role, d) for d in role_fn)
        leftover_sys.extend((role, d) for d in role_fp)

    cross_matched, remaining_gold, remaining_sys = greedy_match(
        leftover_gold, leftover_sys,
        lambda item: span_of(item[1]), lambda item: span_of(item[1]), mode
    )
    cross_role_matches = [(g_role, g_span, s_role, s_span) for (g_role, g_span), (s_role, s_span) in cross_matched]
    return same_role_matches, cross_role_matches, remaining_gold, remaining_sys


# ═══ Precision / recall / F1 ══════════════════════════════════════════════════

def prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def score_srl(gold_conversations, sys_conversations, mode):
    """Precision/recall/F1 for the activity span and each semantic-role category, strict
    (exact offset/length) or lenient (overlapping offset). Also returns the matched
    (gold_span, sys_span) pairs per category, reused by score_types() for lenient mode.

    In lenient mode, an additional "participant" category is included: agent, patient,
    agent_patient, and experiencer pooled together (via match_participant_roles), scoring
    whether the participant span was found at all regardless of which of the four specific
    roles gold and system each assigned it to. This is a supplementary, alternative view of
    the same spans already scored per-role above -- it is NOT included in "overall" (that
    would double-count those spans).

    Only chats present in gold are evaluated; system chats gold doesn't cover are ignored
    (see filter_to_gold_chats).
    """
    sys_conversations = filter_to_gold_chats(sys_conversations, gold_conversations)
    gold_origins = build_origin_lookups(gold_conversations)
    sys_origins = build_origin_lookups(sys_conversations)
    gold_by_key = {(c, t): out for c, t, _u, out in flatten_turns(gold_conversations)}
    sys_by_key = {(c, t): out for c, t, _u, out in flatten_turns(sys_conversations)}
    all_keys = sorted(set(gold_by_key) | set(sys_by_key))

    extra_cats = ["participant"] if mode == "lenient" else []
    counts = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in ["activity"] + ROLE_FIELDS + extra_cats}
    matched_pairs_by_cat = {cat: [] for cat in ["activity"] + ROLE_FIELDS + extra_cats}

    for chat_id, turn_num in all_keys:
        gold_outputs = gold_by_key.get((chat_id, turn_num), [])
        sys_outputs = sys_by_key.get((chat_id, turn_num), [])

        entry_matches, unmatched_gold, unmatched_sys = match_entries_for_turn(
            gold_outputs, sys_outputs, chat_id, gold_origins, sys_origins, mode
        )

        # activity: only entries that carry their OWN value/offset/length are span-scored;
        # a matched pair where both sides are bare references has no span to compare.
        for g, s in entry_matches:
            g_act, s_act = g.get("activity") or {}, s.get("activity") or {}
            if g_act.get("value") is not None and s_act.get("value") is not None:
                counts["activity"]["tp"] += 1
                matched_pairs_by_cat["activity"].append((g_act, s_act))
            elif g_act.get("value") is not None:
                counts["activity"]["fn"] += 1
            elif s_act.get("value") is not None:
                counts["activity"]["fp"] += 1
        for g in unmatched_gold:
            if (g.get("activity") or {}).get("value") is not None:
                counts["activity"]["fn"] += 1
        for s in unmatched_sys:
            if (s.get("activity") or {}).get("value") is not None:
                counts["activity"]["fp"] += 1

        # roles: scored within matched entry-pairs; an unmatched entry's role spans all
        # count against it (FN for gold, FP for system) since there is no counterpart turn.
        for role in ROLE_FIELDS:
            for g, s in entry_matches:
                role_matched, role_fn, role_fp = match_role_spans(g, s, role, mode)
                counts[role]["tp"] += len(role_matched)
                counts[role]["fn"] += len(role_fn)
                counts[role]["fp"] += len(role_fp)
                matched_pairs_by_cat[role].extend(role_matched)
            for g in unmatched_gold:
                counts[role]["fn"] += len([d for d in (g.get(role) or []) if span_of(d) is not None])
            for s in unmatched_sys:
                counts[role]["fp"] += len([d for d in (s.get(role) or []) if span_of(d) is not None])

        # participant: agent/patient/agent_patient/experiencer pooled, lenient only -- see
        # match_participant_roles for why a two-pass (same-role first) match is used instead
        # of a single flat pool-and-match.
        if mode == "lenient":
            for g, s in entry_matches:
                same_matches, cross_matches, remaining_gold, remaining_sys = match_participant_roles(g, s, mode)
                counts["participant"]["tp"] += len(same_matches) + len(cross_matches)
                counts["participant"]["fn"] += len(remaining_gold)
                counts["participant"]["fp"] += len(remaining_sys)
                matched_pairs_by_cat["participant"].extend(same_matches)
                matched_pairs_by_cat["participant"].extend((gs, ss) for (_, gs, _, ss) in cross_matches)
            for g in unmatched_gold:
                counts["participant"]["fn"] += len(
                    [d for role in PARTICIPANT_ROLE_ORDER for d in (g.get(role) or []) if span_of(d) is not None]
                )
            for s in unmatched_sys:
                counts["participant"]["fp"] += len(
                    [d for role in PARTICIPANT_ROLE_ORDER for d in (s.get(role) or []) if span_of(d) is not None]
                )

    report = {}
    tp_sum = fp_sum = fn_sum = 0
    for cat, c in counts.items():
        p, r, f1 = prf(c["tp"], c["fp"], c["fn"])
        report[cat] = {"tp": c["tp"], "fp": c["fp"], "fn": c["fn"], "precision": p, "recall": r, "f1": f1}
        if cat != "participant":  # supplementary alternative view of the same role spans -- would double-count "overall"
            tp_sum += c["tp"]; fp_sum += c["fp"]; fn_sum += c["fn"]
    p, r, f1 = prf(tp_sum, fp_sum, fn_sum)
    report["overall"] = {"tp": tp_sum, "fp": fp_sum, "fn": fn_sum, "precision": p, "recall": r, "f1": f1}
    return report, matched_pairs_by_cat


# ═══ BLANC (activity coreference) ═════════════════════════════════════════════

def blanc_score(rc, ck, cg, rn, nk, ng):
    """Standard BLANC (Recasens & Hovy 2011): average of the coreference-link F1 and the
    non-coreference-link F1, falling back to whichever is defined if the other has no
    denominator (e.g. every mention is a coreference singleton in both gold and system)."""
    def safe_prf(r, k, g):
        p = r / k if k else None
        rec = r / g if g else None
        f = 2 * p * rec / (p + rec) if (p is not None and rec is not None and (p + rec) > 0) else None
        return p, rec, f

    pc, rcv, fc = safe_prf(rc, ck, cg)
    pn, rnv, fn_ = safe_prf(rn, nk, ng)
    if fc is None and fn_ is None:
        blanc = None
    elif fc is None:
        blanc = fn_
    elif fn_ is None:
        blanc = fc
    else:
        blanc = (fc + fn_) / 2
    return {"blanc": blanc, "precision_c": pc, "recall_c": rcv, "f1_c": fc,
            "precision_n": pn, "recall_n": rnv, "f1_n": fn_,
            "rc": rc, "ck": ck, "cg": cg, "rn": rn, "nk": nk, "ng": ng}


def score_blanc(gold_conversations, sys_conversations, mode):
    """BLANC score for activity-reference (coreference) chains: does the system group turn
    mentions of the same real-world activity under one activity_id the same way gold does?

    Mentions are aligned across gold/system per-turn via match_entries_for_turn (so a
    "mention" here is a (gold_entry, sys_entry) pair the aligner considers the same activity
    mention). Two mentions are coreferent in gold/system if their respective entries share
    the same (gold- or system-side) activity_id. BLANC is computed per chat over all pairs
    of aligned mentions in that chat (activity_id links only make sense within a chat), plus
    an aggregate over all chats.

    Only chats present in gold are evaluated; system chats gold doesn't cover are ignored
    (see filter_to_gold_chats).
    """
    sys_conversations = filter_to_gold_chats(sys_conversations, gold_conversations)
    gold_origins = build_origin_lookups(gold_conversations)
    sys_origins = build_origin_lookups(sys_conversations)
    gold_by_key = {(c, t): out for c, t, _u, out in flatten_turns(gold_conversations)}
    sys_by_key = {(c, t): out for c, t, _u, out in flatten_turns(sys_conversations)}

    keys_by_chat = defaultdict(list)
    for chat_id, turn_num in sorted(set(gold_by_key) | set(sys_by_key)):
        keys_by_chat[chat_id].append(turn_num)

    per_chat = {}
    agg = {"rc": 0, "ck": 0, "cg": 0, "rn": 0, "nk": 0, "ng": 0}
    for chat_id, turns in keys_by_chat.items():
        mentions = []
        for turn_num in turns:
            gold_outputs = gold_by_key.get((chat_id, turn_num), [])
            sys_outputs = sys_by_key.get((chat_id, turn_num), [])
            matched, _, _ = match_entries_for_turn(gold_outputs, sys_outputs, chat_id, gold_origins, sys_origins, mode)
            mentions.extend(matched)

        n = len(mentions)
        rc = ck = cg = rn = nk = ng = 0
        for i in range(n):
            g_i = (mentions[i][0].get("activity") or {}).get("activity_id")
            s_i = (mentions[i][1].get("activity") or {}).get("activity_id")
            for j in range(i + 1, n):
                g_j = (mentions[j][0].get("activity") or {}).get("activity_id")
                s_j = (mentions[j][1].get("activity") or {}).get("activity_id")
                g_same, s_same = g_i == g_j, s_i == s_j
                if g_same:
                    cg += 1
                else:
                    ng += 1
                if s_same:
                    ck += 1
                else:
                    nk += 1
                if g_same and s_same:
                    rc += 1
                if not g_same and not s_same:
                    rn += 1
        stats = blanc_score(rc, ck, cg, rn, nk, ng)
        stats["mentions"] = n
        per_chat[chat_id] = stats
        for k in agg:
            agg[k] += stats[k]

    overall = blanc_score(agg["rc"], agg["ck"], agg["cg"], agg["rn"], agg["nk"], agg["ng"])
    overall["mentions"] = sum(c["mentions"] for c in per_chat.values())
    per_chat["overall"] = overall
    return per_chat


# ═══ Type accuracy over leniently matched spans ═══════════════════════════════

def score_types(gold_conversations, sys_conversations):
    """For every span that leniently matches between gold and system (activity + each typed
    role, "time" excluded since it has no type), is the assigned type also correct?"""
    _, matched_pairs = score_srl(gold_conversations, sys_conversations, mode="lenient")
    report = {}
    correct_total = total_total = 0
    for cat in TYPED_FIELDS:
        pairs = matched_pairs[cat]
        correct = sum(1 for g, s in pairs if g.get("type") == s.get("type"))
        total = len(pairs)
        report[cat] = {"correct": correct, "total": total, "accuracy": (correct / total) if total else None}
        correct_total += correct
        total_total += total
    report["overall"] = {"correct": correct_total, "total": total_total,
                          "accuracy": (correct_total / total_total) if total_total else None}
    return report


# ═══ Chat-level character n-gram matching (offset-free) ═══════════════════════

NGRAM_SIZE = 3
NGRAM_THRESHOLD = 0.5


def char_ngrams(s, n=NGRAM_SIZE):
    """Character n-grams of the lowercased string, as a multiset. A string shorter than n
    falls back to itself as a single "gram", so a short exact match (e.g. "I" vs "I") still
    scores 1.0 instead of 0 for having no n-grams at all."""
    s = s.lower()
    if not s:
        return Counter()
    if len(s) < n:
        return Counter([s])
    return Counter(s[i:i + n] for i in range(len(s) - n + 1))


def ngram_overlap(a, b, n=NGRAM_SIZE):
    """Character n-gram Dice coefficient in [0, 1]: 2*|shared n-grams| / (|a's n-grams| +
    |b's n-grams|), counting n-grams as multisets so repeated substrings contribute more than
    once. 1.0 if both strings are empty, 0.0 if only one of them is."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    ca, cb = char_ngrams(a, n), char_ngrams(b, n)
    shared = sum((ca & cb).values())
    total = sum(ca.values()) + sum(cb.values())
    return 2 * shared / total if total else 0.0


def greedy_match_ngram(gold_items, sys_items, score_fn, threshold=NGRAM_THRESHOLD):
    """One-to-one alignment of gold_items to sys_items by a similarity score (score_fn(g, s) ->
    float in [0, 1], typically ngram_overlap or best_mention_overlap) instead of by offset: each
    gold item takes the best available (highest-scoring) unused system item whose score is >=
    threshold. Returns (matched_pairs, unmatched_gold, unmatched_sys); matched_pairs is
    [(gold_item, sys_item), ...] -- mirrors greedy_match's shape and greedy-best-first strategy,
    but the match criterion is a similarity threshold rather than exact/overlapping offsets."""
    remaining = list(enumerate(sys_items))
    matched = []
    unmatched_gold = []
    for g in gold_items:
        best_idx, best_item, best_score = None, None, -1
        for idx, s in remaining:
            score = score_fn(g, s)
            if score >= threshold and score > best_score:
                best_score, best_idx, best_item = score, idx, s
        if best_item is not None:
            matched.append((g, best_item))
            remaining = [(i, s) for i, s in remaining if i != best_idx]
        else:
            unmatched_gold.append(g)
    unmatched_sys = [s for _, s in remaining]
    return matched, unmatched_gold, unmatched_sys


def best_mention_overlap(gold_mentions, sys_mentions, n=NGRAM_SIZE):
    """Best-case similarity between two activity coreference chains: the highest n-gram overlap
    between any single gold mention and any single system mention, rather than concatenating
    all mentions into one blob first. This credits an activity chain if AT LEAST ONE phrasing
    lines up between gold and system, even if the chains' other mentions or turn coverage
    differ -- mirroring how turn-level lenient scoring gives partial credit per mention instead
    of requiring an entire chain to agree at once. Concatenating all mentions into one blob
    first (the alternative) can dilute the score below threshold even when one mention matches
    exactly, if the chain's other mentions use different wording or the chains differ in length."""
    if not gold_mentions or not sys_mentions:
        return 0.0
    return max(ngram_overlap(g, s, n) for g in gold_mentions for s in sys_mentions)


def activity_mentions_by_chat(conversations):
    """chat_id -> {activity_id: [mention_value, ...]}. Every entry that names its activity with
    its OWN value (as opposed to a bare reference entry that carries only an activity_id) is a
    co-referring mention of that activity; the list holds every phrasing used for it anywhere in
    the chat, in turn order, kept separate (not joined) so activity matching can compare mentions
    pairwise (see best_mention_overlap) rather than requiring a whole chain to agree at once."""
    by_chat = defaultdict(lambda: defaultdict(list))
    for chat_id, _turn, _utt, outputs in flatten_turns(conversations):
        for entry in outputs:
            act = entry.get("activity") or {}
            aid, value = act.get("activity_id"), act.get("value")
            if aid is not None and value is not None:
                by_chat[chat_id][aid].append(value)
    return {chat_id: dict(acts) for chat_id, acts in by_chat.items()}


def pool_role_values_by_chat(conversations, role):
    """chat_id -> [value, ...]: every individual value for `role`, across every entry and every
    turn in the chat -- offsets and turn boundaries ignored, unlike match_role_spans. Unlike
    activities, individual role fillers have no coreference identifier of their own, so they
    are matched value-by-value rather than grouped first."""
    by_chat = defaultdict(list)
    for chat_id, _turn, _utt, outputs in flatten_turns(conversations):
        for entry in outputs:
            for d in (entry.get(role) or []):
                if d.get("value") is not None:
                    by_chat[chat_id].append(d["value"])
    return by_chat


def _prf_report(counts):
    report = {}
    tp_sum = fp_sum = fn_sum = 0
    for cat, c in counts.items():
        p, r, f1 = prf(c["tp"], c["fp"], c["fn"])
        report[cat] = {"tp": c["tp"], "fp": c["fp"], "fn": c["fn"], "precision": p, "recall": r, "f1": f1}
        tp_sum += c["tp"]; fp_sum += c["fp"]; fn_sum += c["fn"]
    p, r, f1 = prf(tp_sum, fp_sum, fn_sum)
    report["overall"] = {"tp": tp_sum, "fp": fp_sum, "fn": fn_sum, "precision": p, "recall": r, "f1": f1}
    return report


def score_chat_ngram(gold_conversations, sys_conversations, threshold=NGRAM_THRESHOLD, n=NGRAM_SIZE):
    """Per-chat, offset-free precision/recall/F1 for the activity and each semantic-role
    category, matching by character n-gram overlap of the expression text (ngram_overlap)
    instead of by offset -- a coarser, position-independent measure of "did the system find
    the same activities and role fillers", complementing score_srl's offset-anchored scoring.

    Activities are matched as coreference chains, but not by concatenating a chain into one
    blob: entries are grouped by activity_id into their list of mentions
    (activity_mentions_by_chat), and a gold chain matches a system chain if their single best
    mention pairing (best_mention_overlap) clears the threshold -- crediting a chain if at least
    one phrasing lines up, whatever the rest of its mentions look like. Roles are matched
    value-by-value, pooling every individual role value anywhere in the chat
    (pool_role_values_by_chat) -- an individual role filler has no coreference identifier the
    way an activity does, so there is no chain to take the best mention of.

    A pair counts as a match if its similarity score is >= threshold (default 0.5), via
    greedy_match_ngram (one-to-one, best-score-first).

    Returns {chat_id: report, ..., "average": report}; report is shaped like score_srl's (per
    category: tp/fp/fn/precision/recall/f1, plus "overall"). "average" is the unweighted
    (macro) mean of every metric across chats. Only chats present in gold are evaluated (see
    filter_to_gold_chats).
    """
    sys_conversations = filter_to_gold_chats(sys_conversations, gold_conversations)
    gold_activities = activity_mentions_by_chat(gold_conversations)
    sys_activities = activity_mentions_by_chat(sys_conversations)
    gold_role_pools = {role: pool_role_values_by_chat(gold_conversations, role) for role in ROLE_FIELDS}
    sys_role_pools = {role: pool_role_values_by_chat(sys_conversations, role) for role in ROLE_FIELDS}
    gold_chat_ids = {c for c, _t, _u, _o in flatten_turns(gold_conversations)}
    sys_chat_ids = {c for c, _t, _u, _o in flatten_turns(sys_conversations)}
    chat_ids = sorted(gold_chat_ids | sys_chat_ids)

    per_chat = {}
    for chat_id in chat_ids:
        counts = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat in ["activity"] + ROLE_FIELDS}

        gold_act_items = list(gold_activities.get(chat_id, {}).items())  # (activity_id, [mentions])
        sys_act_items = list(sys_activities.get(chat_id, {}).items())
        matched, unmatched_gold, unmatched_sys = greedy_match_ngram(
            gold_act_items, sys_act_items,
            lambda g, s: best_mention_overlap(g[1], s[1], n),
            threshold,
        )
        counts["activity"]["tp"] = len(matched)
        counts["activity"]["fn"] = len(unmatched_gold)
        counts["activity"]["fp"] = len(unmatched_sys)

        for role in ROLE_FIELDS:
            gold_vals = gold_role_pools[role].get(chat_id, [])
            sys_vals = sys_role_pools[role].get(chat_id, [])
            r_matched, r_fn, r_fp = greedy_match_ngram(
                gold_vals, sys_vals, lambda g, s: ngram_overlap(g, s, n), threshold
            )
            counts[role]["tp"] = len(r_matched)
            counts[role]["fn"] = len(r_fn)
            counts[role]["fp"] = len(r_fp)

        per_chat[chat_id] = _prf_report(counts)

    cats = ["activity"] + ROLE_FIELDS + ["overall"]
    n_chats = len(chat_ids)
    average = {
        cat: {
            metric: (sum(per_chat[c][cat][metric] for c in chat_ids) / n_chats if n_chats else 0.0)
            for metric in ("tp", "fp", "fn", "precision", "recall", "f1")
        }
        for cat in cats
    }
    per_chat["average"] = average
    return per_chat


# ═══ Side-by-side gold/system mismatches ══════════════════════════════════════

# First/second-person pronoun forms. With exactly two participants per conversation (the
# patient and the coach), any of these -- in a person role -- necessarily refers to one of
# them correctly, regardless of which specific span gold chose to anchor.
SPEAKER_PRONOUNS = {
    "i", "me", "my", "mine", "myself",
    "you", "your", "yours", "yourself",
    "we", "us", "our", "ours",
    "i'm", "i've", "i'll", "i'd",
    "you're", "you've", "you'll", "you'd",
    "we're", "we've", "we'll", "we'd",
}


def value_occurs_in_utterance(value, utterance):
    """Exact then case-insensitive substring check -- mirrors locate_phrase() in
    llm_event_triples_openai_pydantic.py / locatePhrase() in annotation_tool.html."""
    if not value or not utterance:
        return False
    return value in utterance or value.lower() in utterance.lower()


def is_speaker_reference(value, human_name=None):
    """True if `value` refers to a conversation participant either as a first/second-person
    pronoun, or by the patient's own name (e.g. gold says "Jan", system says "you" -- both
    correctly refer to the same person, just via a different kind of expression)."""
    if not value:
        return False
    normalized = value.strip().strip("\"'").lower()
    if normalized in SPEAKER_PRONOUNS:
        return True
    return bool(human_name) and normalized == human_name.strip().lower()


def turn_has_speaker_reference(outputs, role, human_name=None):
    """True if ANY entry in this turn's Output list has, for `role`, a value that refers to a
    speaker (pronoun or the patient's name -- see is_speaker_reference). Used to require that
    gold ALSO independently identifies a speaker reference for a role before trusting the
    system's own extraction there as a genuine SPEAKER MATCH, rather than a role gold never
    populates that way."""
    if role not in PARTICIPANT_ROLES:
        return False
    return any(is_speaker_reference(d.get("value"), human_name) for entry in outputs for d in (entry.get(role) or []))


def classify_system_mismatch(value, category, utterance, gold_has_speaker_reference, human_name=None):
    """Classify a system-only (false positive) mismatch value:
    - "hallucination": the value doesn't occur anywhere in the turn's utterance at all --
      fabricated, often actually the text of a DIFFERENT turn the model confused this one with.
    - "speaker_match": the value does occur, refers to a speaker -- a first/second-person
      pronoun or the patient's own name (see is_speaker_reference) -- filling a person role
      (agent/patient/agent_patient/experiencer), AND gold independently makes its own speaker
      reference for that SAME role in this turn (gold_has_speaker_reference), regardless of
      whether gold used a name and system used a pronoun or vice versa -- i.e. this isn't just
      "any pronoun in a person slot", it's the system correctly identifying the same person
      gold identifies for that role, just not via the exact span/expression gold chose.
    - None: an ordinary mismatch.
    """
    if not value_occurs_in_utterance(value, utterance):
        return "hallucination"
    if category in PARTICIPANT_ROLES and is_speaker_reference(value, human_name) and gold_has_speaker_reference:
        return "speaker_match"
    return None


def _span_summary(d):
    if d is None:
        return None
    return {"value": d.get("value"), "offset": d.get("offset"), "length": d.get("length"), "type": d.get("type")}


def _mismatch_record(chat_id, turn_num, utterance, category, gold_span, sys_span,
                      gold_has_speaker_reference=False, human_name=None):
    gold_summary = _span_summary(gold_span)
    sys_summary = _span_summary(sys_span)
    flag = None
    if sys_summary is not None and sys_summary.get("value"):
        flag = classify_system_mismatch(sys_summary["value"], category, utterance,
                                         gold_has_speaker_reference, human_name)
    return {"chat": chat_id, "turn": turn_num, "utterance": utterance, "category": category,
            "gold": gold_summary, "system": sys_summary, "flag": flag}


def _participant_match_record(chat_id, turn_num, utterance, gold_role, gold_span, sys_role, sys_span):
    """A gold item in one participant role and a system item in a DIFFERENT participant role
    (agent/patient/agent_patient/experiencer) whose spans overlap -- the same real participant,
    just assigned a different specific role by gold vs. system. Not run through
    classify_system_mismatch: by construction (found via an overlapping-span match) the system
    value is grounded in the utterance and matches gold, so it can be neither a hallucination
    nor an ordinary mismatch."""
    return {"chat": chat_id, "turn": turn_num, "utterance": utterance, "category": f"{gold_role}/{sys_role}",
            "gold": _span_summary(gold_span), "system": _span_summary(sys_span), "flag": "participant_match"}


def collect_mismatches(gold_conversations, sys_conversations):
    """For every turn and category (activity + each role), list every gold-only (FN) and
    system-only (FP) item under LENIENT (overlapping-offset) matching -- i.e. exactly what
    score_srl(mode="lenient") would count as FN/FP, but as full records instead of a tally,
    for side-by-side inspection. Ordered by (chat, turn), then activity before roles in
    ROLE_FIELDS order. Only chats present in gold are considered (see filter_to_gold_chats).

    Each record's "flag" is either "participant_match" (a gold item and a system item in
    different participant roles -- agent/patient/agent_patient/experiencer -- whose spans
    overlap; see match_participant_roles), or, for other system-only records, whatever
    classify_system_mismatch() returns: "hallucination", "speaker_match", or None.

    Returns (records, total_turns) -- total_turns is the number of (chat, turn) pairs
    considered, i.e. the denominator for the hallucination score in write_mismatch_log().
    """
    mode = "lenient"
    sys_conversations = filter_to_gold_chats(sys_conversations, gold_conversations)
    gold_origins = build_origin_lookups(gold_conversations)
    sys_origins = build_origin_lookups(sys_conversations)
    human_by_chat = build_human_by_chat(gold_conversations)
    gold_by_key = {(c, t): (u, out) for c, t, u, out in flatten_turns(gold_conversations)}
    sys_by_key = {(c, t): (u, out) for c, t, u, out in flatten_turns(sys_conversations)}
    all_keys = sorted(set(gold_by_key) | set(sys_by_key))

    records = []
    for chat_id, turn_num in all_keys:
        gold_u, gold_outputs = gold_by_key.get((chat_id, turn_num), (None, []))
        sys_u, sys_outputs = sys_by_key.get((chat_id, turn_num), (None, []))
        utterance = gold_u if gold_u is not None else sys_u
        human_name = human_by_chat.get(chat_id)

        entry_matches, unmatched_gold, unmatched_sys = match_entries_for_turn(
            gold_outputs, sys_outputs, chat_id, gold_origins, sys_origins, mode
        )

        # Precompute, per role, whether GOLD independently makes a speaker reference (pronoun
        # or the patient's name) for that role ANYWHERE in this turn (across all of gold's
        # entries, not just the ones involved in a given mismatch) -- required for a system
        # value in that role to count as a genuine SPEAKER MATCH rather than an invented role.
        gold_speaker_by_role = {role: turn_has_speaker_reference(gold_outputs, role, human_name) for role in ROLE_FIELDS}

        for g, s in entry_matches:
            g_act, s_act = g.get("activity") or {}, s.get("activity") or {}
            if g_act.get("value") is not None and s_act.get("value") is None:
                records.append(_mismatch_record(chat_id, turn_num, utterance, "activity", g_act, None))
            elif s_act.get("value") is not None and g_act.get("value") is None:
                records.append(_mismatch_record(chat_id, turn_num, utterance, "activity", None, s_act))
        for g in unmatched_gold:
            g_act = g.get("activity") or {}
            if g_act.get("value") is not None:
                records.append(_mismatch_record(chat_id, turn_num, utterance, "activity", g_act, None))
        for s in unmatched_sys:
            s_act = s.get("activity") or {}
            if s_act.get("value") is not None:
                records.append(_mismatch_record(chat_id, turn_num, utterance, "activity", None, s_act))

        non_participant_roles = [r for r in ROLE_FIELDS if r not in PARTICIPANT_ROLES]
        for role in non_participant_roles:
            for g, s in entry_matches:
                _, role_fn, role_fp = match_role_spans(g, s, role, mode)
                for d in role_fn:
                    records.append(_mismatch_record(chat_id, turn_num, utterance, role, d, None))
                for d in role_fp:
                    records.append(_mismatch_record(chat_id, turn_num, utterance, role, None, d))
            for g in unmatched_gold:
                for d in (g.get(role) or []):
                    if span_of(d) is not None:
                        records.append(_mismatch_record(chat_id, turn_num, utterance, role, d, None))
            for s in unmatched_sys:
                for d in (s.get(role) or []):
                    if span_of(d) is not None:
                        records.append(_mismatch_record(chat_id, turn_num, utterance, role, None, d))

        # Participant roles (agent/patient/agent_patient/experiencer): within each matched
        # entry pair, first match same-role as usual, then pool whatever's left across all
        # four roles -- a leftover gold item and leftover system item that overlap despite
        # different roles are the same real participant, mislabeled, flagged as a
        # PARTICIPANT MATCH rather than reported as two independent FN/FP mismatches.
        for g, s in entry_matches:
            _, cross_matches, remaining_gold, remaining_sys = match_participant_roles(g, s, mode)
            for g_role, g_span, s_role, s_span in cross_matches:
                records.append(_participant_match_record(chat_id, turn_num, utterance, g_role, g_span, s_role, s_span))
            for role, d in remaining_gold:
                records.append(_mismatch_record(chat_id, turn_num, utterance, role, d, None))
            for role, d in remaining_sys:
                records.append(_mismatch_record(chat_id, turn_num, utterance, role, None, d, gold_speaker_by_role[role], human_name))
        for role in PARTICIPANT_ROLE_ORDER:
            for g in unmatched_gold:
                for d in (g.get(role) or []):
                    if span_of(d) is not None:
                        records.append(_mismatch_record(chat_id, turn_num, utterance, role, d, None))
            for s in unmatched_sys:
                for d in (s.get(role) or []):
                    if span_of(d) is not None:
                        records.append(_mismatch_record(chat_id, turn_num, utterance, role, None, d, gold_speaker_by_role[role], human_name))

    return records, len(all_keys)


def _format_side(span):
    if span is None:
        return "--"
    offset, length, typ = span.get("offset"), span.get("length"), span.get("type")
    loc = f"[{offset}:{offset + length}]" if offset is not None and length is not None else ""
    type_part = f" type={typ}" if typ is not None else ""
    return f"{span.get('value')!r} {loc}{type_part}".strip()


def write_mismatch_log(records, total_turns, path):
    hallucinations = sum(1 for r in records if r["flag"] == "hallucination")
    speaker_matches = sum(1 for r in records if r["flag"] == "speaker_match")
    participant_matches = sum(1 for r in records if r["flag"] == "participant_match")
    hallucination_score = (hallucinations / total_turns) if total_turns else None
    score_str = f"{hallucination_score:.3f}" if hallucination_score is not None else "n/a"

    with open(path, "w") as f:
        f.write("# Auto-generated by evaluate.py -- side-by-side gold/system mismatches (lenient matching)\n")
        f.write(f"# {len(records)} mismatches (false negatives = gold-only, false positives = system-only)\n")
        f.write(f"# {hallucinations} HALLUCINATION(s): system value not found anywhere in the turn's utterance\n")
        f.write(f"# {speaker_matches} SPEAKER MATCH(es): system value refers to a speaker (a pronoun or the\n")
        f.write("#   patient's own name) for a role where gold ALSO makes a speaker reference (pronoun or\n")
        f.write("#   name, not necessarily the same kind), just not aligned with the specific span gold chose\n")
        f.write(f"# {participant_matches} PARTICIPANT MATCH(es): gold and system found the same participant span but\n")
        f.write("#   filed it under different roles among agent/patient/agent_patient/experiencer\n")
        f.write(f"# Hallucination score: {hallucinations}/{total_turns} = {score_str}\n")
        current_key = None
        for rec in records:
            key = (rec["chat"], rec["turn"])
            if key != current_key:
                current_key = key
                f.write(f"\nchat {rec['chat']} turn {rec['turn']}: \"{rec['utterance']}\"\n")
            gold_str = _format_side(rec["gold"])
            sys_str = _format_side(rec["system"])
            tag = f" [{rec['flag'].upper().replace('_', ' ')}]" if rec["flag"] else ""
            f.write(f"  {rec['category']:<14} GOLD: {gold_str:<45} | SYSTEM: {sys_str}{tag}\n")
    print(f"Wrote {path} ({hallucinations} hallucinations, {speaker_matches} speaker matches, "
          f"{participant_matches} participant matches, hallucination score {score_str})")


# ═══ Report output: JSON + LaTeX ═══════════════════════════════════════════════

def esc_tex(s):
    """Escape the handful of LaTeX-special characters that can appear in a category
    name or chat id (mainly the underscore in role names like agent_patient)."""
    s = str(s)
    for ch in ("\\", "_", "%", "&", "#"):
        s = s.replace(ch, "\\" + ch)
    return s


def fmt_tex(x, spec=".3f"):
    return format(x, spec) if x is not None else "--"


def srl_table_tex(report, mode):
    cats = ["activity"] + ROLE_FIELDS + (["participant"] if "participant" in report else []) + ["overall"]
    rows = "\n".join(
        f"{esc_tex(cat)} & {report[cat]['tp']} & {report[cat]['fp']} & {report[cat]['fn']} & "
        f"{fmt_tex(report[cat]['precision'])} & {fmt_tex(report[cat]['recall'])} & {fmt_tex(report[cat]['f1'])} \\\\"
        for cat in cats
    )
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lrrrrrr}\n\\toprule\n"
        "Category & TP & FP & FN & Precision & Recall & F1 \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        f"\\caption{{SRL scores ({mode})}}\n"
        f"\\label{{tab:srl-{mode}}}\n"
        "\\end{table}\n"
    )


def blanc_table_tex(report, mode):
    rows = "\n".join(
        f"{esc_tex(chat_id)} & {c['mentions']} & {fmt_tex(c['blanc'])} & {fmt_tex(c['f1_c'])} & {fmt_tex(c['f1_n'])} \\\\"
        for chat_id, c in report.items() if chat_id != "overall"
    )
    o = report["overall"]
    rows += (f"\n\\midrule\nOverall & {o['mentions']} & {fmt_tex(o['blanc'])} & "
             f"{fmt_tex(o['f1_c'])} & {fmt_tex(o['f1_n'])} \\\\")
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lrrrr}\n\\toprule\n"
        "Chat & Mentions & BLANC & Coref F1 & Non-coref F1 \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        f"\\caption{{BLANC activity-coreference scores ({mode} mention alignment)}}\n"
        f"\\label{{tab:blanc-{mode}}}\n"
        "\\end{table}\n"
    )


def types_table_tex(report):
    rows = "\n".join(
        f"{esc_tex(cat)} & {report[cat]['correct']} & {report[cat]['total']} & {fmt_tex(report[cat]['accuracy'])} \\\\"
        for cat in TYPED_FIELDS + ["overall"]
    )
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lrrr}\n\\toprule\n"
        "Category & Correct & Total & Accuracy \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        "\\caption{Type accuracy (over leniently matched spans)}\n"
        "\\label{tab:type-accuracy}\n"
        "\\end{table}\n"
    )


def fmt_count(x):
    """tp/fp/fn are integers per chat but (possibly fractional) means in the "average" row."""
    return str(x) if isinstance(x, int) else f"{x:.2f}"


def chat_ngram_table_tex(report, caption, label):
    rows = "\n".join(
        f"{esc_tex(cat)} & {fmt_count(report[cat]['tp'])} & {fmt_count(report[cat]['fp'])} & {fmt_count(report[cat]['fn'])} & "
        f"{fmt_tex(report[cat]['precision'])} & {fmt_tex(report[cat]['recall'])} & {fmt_tex(report[cat]['f1'])} \\\\"
        for cat in ["activity"] + ROLE_FIELDS + ["overall"]
    )
    return (
        "\\begin{table}[htbp]\n\\centering\n"
        "\\begin{tabular}{lrrrrrr}\n\\toprule\n"
        "Category & TP & FP & FN & Precision & Recall & F1 \\\\\n\\midrule\n"
        f"{rows}\n"
        "\\bottomrule\n\\end{tabular}\n"
        f"\\caption{{{esc_tex(caption)}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{table}\n"
    )


def write_outputs(results, tex_sections, json_path, tex_path):
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    with open(tex_path, "w") as f:
        f.write("% Auto-generated by evaluate.py -- do not edit by hand.\n\n")
        f.write("\n".join(tex_sections))
    print(f"Wrote {json_path}")
    print(f"Wrote {tex_path}")


# ═══ CLI ═══════════════════════════════════════════════════════════════════════

def parse_args():
    # Shared flags, attached ONLY to each subparser (not the top-level parser): argparse
    # subparsers fill in their own defaults after the top level parses, which would silently
    # overwrite a same-named flag given before the subcommand. Keeping these subparser-only
    # means "evaluate.py srl --tex out.tex" works and there is no ambiguous dual placement.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--gold", default="annotation/annotations.json",
                         help="Path to the gold-standard (manually annotated) JSON file (default: annotation/annotations.json).")
    common.add_argument("--system", default="../../data/event_srl.json",
                         help="Path to the system (LLM) output JSON file (default: ../../data/event_srl.json).")
    common.add_argument("--output", default=".",
                         help="Output folder for the report files (default: current directory); created if it "
                              "doesn't exist. Files are written there under their default names: "
                              "evaluation_<command>.json, evaluation_<command>.tex, and evaluation_mismatches.log "
                              "(mismatches) or evaluation_all_mismatches.log (all).")

    parser = argparse.ArgumentParser(
        description="Evaluate LLM-generated SRL annotations against the manually annotated gold standard."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    srl_p = sub.add_parser("srl", parents=[common], help="Precision/recall/F1 for the activity span and each semantic role.")
    srl_p.add_argument("--mode", choices=["strict", "lenient", "both"], default="both",
                        help="strict = exact offset/length match; lenient = overlapping offsets.")

    blanc_p = sub.add_parser("blanc", parents=[common], help="BLANC score for activity coreference (activity_id chains).")
    blanc_p.add_argument("--mode", choices=["strict", "lenient", "both"], default="both",
                          help="How mentions are aligned across gold/system before scoring coreference links.")

    sub.add_parser("types", parents=[common], help="Type accuracy for activity/role types, over leniently matched spans.")

    ngram_p = sub.add_parser("ngram", parents=[common],
                              help="Per-chat, offset-free precision/recall/F1 via character n-gram overlap of "
                                   "activity/role text (activities matched by best mention within their activity_id "
                                   "chain), plus the "
                                   "average across chats. One table per chat.")
    ngram_p.add_argument("--threshold", type=float, default=NGRAM_THRESHOLD,
                          help=f"Minimum n-gram overlap (Dice coefficient, 0-1) to count as a match (default {NGRAM_THRESHOLD}).")
    ngram_p.add_argument("--ngram-size", type=int, default=NGRAM_SIZE, dest="ngram_size",
                          help=f"Character n-gram size (default {NGRAM_SIZE}).")

    sub.add_parser("mismatches", parents=[common],
                    help="Side-by-side log of gold-only and system-only activity/role spans (lenient matching), "
                         "flagging hallucinations, speaker matches, and participant-role matches, with a "
                         "hallucination score.")

    sub.add_parser("all", parents=[common],
                    help="Run srl (strict+lenient), blanc (strict+lenient), types, ngram, and a lenient mismatch log.")

    return parser.parse_args()

# Howto:
#CLI: python evaluate.py {srl,blanc,types,mismatches,all} [--mode strict|lenient|both] [--gold PATH] [--system PATH]
# [--output DIR], defaults pointing at annotation/annotations.json and ../../data/event_srl.json,
# and writing evaluation_<command>.json / .tex / _mismatches.log into DIR (default: cwd) under
# their default names.
#python evaluate.py all --output ../../data


help = '''Run evaluate as follows:

- python evaluate.py all

That scores everything (srl strict + lenient, blanc strict + lenient, types, ngram) using the default files:
-gold: annotation/annotations.json,
-system: ../../data/event_srl.json

It writes evaluation_all.json, evaluation_all.tex and evaluation_all_mismatches.log (lenient
side-by-side gold/system mismatches for activities and roles) in the current directory.

python evaluate.py all --gold annotation/annotations.json --system ../../data/event_srl.json --output ../../data

To run just one evaluation with explicit paths, e.g. lenient-only SRL scoring with a custom output folder:

python evaluate.py srl --mode lenient --gold annotation/annotations.json --system ../../data/event_srl.json --output ../../data

To get just the side-by-side mismatch log (lenient matching only; does not write JSON/LaTeX):

python evaluate.py mismatches --output ../../data

Each system-only mismatch in the log is tagged where applicable: [HALLUCINATION] if the
system's value doesn't occur anywhere in the turn's utterance at all (fabricated -- often
actually the text of a different turn), [SPEAKER MATCH] if it's a speaker reference (a
pronoun or the patient's own name) in a person role AND gold ALSO makes a speaker reference
for that same role in that turn -- just not the exact span or kind of expression gold chose,
or [PARTICIPANT MATCH] if gold and system found the same participant span but filed it under
different roles among agent/patient/agent_patient/experiencer (e.g. gold said agent_patient,
system said patient). The log header reports the hallucination score
(hallucinations / total turns evaluated).

The "srl" command additionally reports a lenient-only "participant" row: agent, patient,
agent_patient, and experiencer pooled into one category, scoring whether the participant span
was found at all regardless of which of those four specific roles gold and system each used.
It is a supplementary view alongside the per-role rows, not included in "overall".

python evaluate.py ngram --gold annotation/annotations.json --system ../../data/event_srl.json --output ../../data

The "ngram" command scores activities and roles per CHAT, ignoring offsets entirely, matching
by character n-gram overlap of the expression text (Dice coefficient over character trigrams
by default; tune with --threshold and --ngram-size) instead of by offset. Activities are
matched as coreference chains, one gold chain to one system chain, but by their single BEST
mention pairing rather than by concatenating each chain into one blob first: every expression
sharing an activity_id is a mention of that chain, and a gold chain matches a system chain if
the highest n-gram overlap between any one of its mentions and any one of the system chain's
mentions clears the threshold -- crediting the chain if at least one phrasing lines up. Roles
are matched value-by-value, pooling every individual value anywhere in the chat. It writes one
table per chat plus one "average" table (the unweighted mean across chats) into
evaluation_ngram.json / evaluation_ngram.tex (or evaluation_all.json / evaluation_all.tex as
part of "all").

Remember: --gold / --system / --output must come after the subcommand
(srl/blanc/types/ngram/mismatches/all), not before.

Evaluation (srl/blanc/types/ngram/mismatches) only considers chats present in the gold file --
any chat in --system that gold doesn't cover is ignored entirely.
'''


def main():
    args = parse_args()
    gold = load_conversations(args.gold)
    system = load_conversations(args.system)
    os.makedirs(args.output, exist_ok=True)

    # "mismatches" produces only a log, not a JSON/LaTeX report.
    if args.command == "mismatches":
        records, total_turns = collect_mismatches(gold, system)
        write_mismatch_log(records, total_turns, os.path.join(args.output, "evaluation_mismatches.log"))
        return

    results = {}
    tex_sections = []

    def add_srl(mode):
        report, _ = score_srl(gold, system, mode)
        results[f"srl_{mode}"] = report
        tex_sections.append(srl_table_tex(report, mode))

    def add_blanc(mode):
        report = score_blanc(gold, system, mode)
        results[f"blanc_{mode}"] = report
        tex_sections.append(blanc_table_tex(report, mode))

    def add_types():
        report = score_types(gold, system)
        results["types"] = report
        tex_sections.append(types_table_tex(report))

    def add_ngram(threshold, ngram_size):
        report = score_chat_ngram(gold, system, threshold=threshold, n=ngram_size)
        results["ngram"] = report
        for chat_id, chat_report in report.items():
            if chat_id == "average":
                tex_sections.append(chat_ngram_table_tex(
                    chat_report, "SRL n-gram overlap scores (average across chats)", "tab:ngram-average"))
            else:
                tex_sections.append(chat_ngram_table_tex(
                    chat_report, f"SRL n-gram overlap scores (chat {chat_id})", f"tab:ngram-chat{chat_id}"))

    if args.command == "srl":
        for mode in (["strict", "lenient"] if args.mode == "both" else [args.mode]):
            add_srl(mode)
    elif args.command == "blanc":
        for mode in (["strict", "lenient"] if args.mode == "both" else [args.mode]):
            add_blanc(mode)
    elif args.command == "types":
        add_types()
    elif args.command == "ngram":
        add_ngram(args.threshold, args.ngram_size)
    elif args.command == "all":
        for mode in ["strict", "lenient"]:
            add_srl(mode)
        for mode in ["strict", "lenient"]:
            add_blanc(mode)
        add_types()
        add_ngram(NGRAM_THRESHOLD, NGRAM_SIZE)

    json_path = os.path.join(args.output, f"evaluation_{args.command}.json")
    tex_path = os.path.join(args.output, f"evaluation_{args.command}.tex")
    write_outputs(results, tex_sections, json_path, tex_path)

    if args.command == "all":
        records, total_turns = collect_mismatches(gold, system)
        write_mismatch_log(records, total_turns, os.path.join(args.output, "evaluation_all_mismatches.log"))


if __name__ == "__main__":
    main()
