"""R60 GLM: opt-in ultra-conservative *literal* quote reconciliation.

Only fixes at most two character-level edits of an already long, anchored
quotation. The replacement is an actual contiguous substring in one approved
body, of very similar length. No candidate list unrelated to the quote, no
changes to decision/scores/severe flags, and no source/target cross-over.

The frozen checkpoint validator still owns acceptance. A repair does not
provide a new independent endorsement of a model's literary assertion.
"""
from __future__ import annotations

from difflib import SequenceMatcher

FIELDS = (
    ("specific_source_quotes", "SOURCE"),
    ("specific_target_quotes", "TARGET"),
)
MIN_QUOTE = 10
MIN_ANCHOR = 6
MAX_EDITS = 2
MIN_RATIO = 0.90


def _candidates(quote: str, body: str):
    """Return small anchored substring proposals, not arbitrary sentences."""
    matcher = SequenceMatcher(None, quote, body, autojunk=False)
    block = max(matcher.get_matching_blocks(), key=lambda b: b.size)
    if block.size < MIN_ANCHOR:
        return []
    start = block.b - block.a
    found = set()
    for delta in (-2, -1, 0, 1, 2):
        for shift in (-2, -1, 0, 1, 2):
            lo = start + shift
            length = len(quote) + delta
            if 0 <= lo < len(body) and 0 < length <= 300:
                if lo + length <= len(body):
                    found.add(body[lo:lo + length])
    return found


def _edit_distance_bounded(a: str, b: str, limit: int = MAX_EDITS) -> int:
    """Levenshtein with a two-edit ceiling; no third-party dependency."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            current[j] = min(current[j - 1] + 1,
                             previous[j] + 1,
                             previous[j - 1] + (ca != cb))
        if min(current) > limit:
            return limit + 1
        previous = current
    return previous[-1]


def reconcile_quote(quote: object, bodies: list[str]) -> str | None:
    """Return exact source-backed near-identical correction or None."""
    if not isinstance(quote, str) or not MIN_QUOTE <= len(quote) <= 300:
        return None
    if not quote.strip() or any(quote in body for body in bodies):
        return None
    candidates = set()
    for body in bodies:
        if not isinstance(body, str):
            return None
        candidates.update(_candidates(quote, body))
    accepted = []
    for candidate in candidates:
        if not candidate.strip() or candidate == quote:
            continue
        if _edit_distance_bounded(quote, candidate) > MAX_EDITS:
            continue
        if SequenceMatcher(None, quote, candidate, autojunk=False).ratio() < MIN_RATIO:
            continue
        accepted.append(candidate)
    # Distinct even-near-identical candidates are ambiguous: no guesses.
    return accepted[0] if len(accepted) == 1 else None


def make_reconciler(worker: object, emit: object):
    """Wrap the original frozen checkpoint_record; preserve error on failure."""
    original = worker.checkpoint_record

    def observed(position, row, response, model, revision):
        if not isinstance(response, dict):
            return original(position, row, response, model, revision)
        updated = None
        edits = 0
        unmatched = 0
        for field, label in FIELDS:
            value = response.get(field)
            if not isinstance(value, list) or len(value) > 12:
                return original(position, row, response, model, revision)
            bodies = (
                [message["content"] for message in row["visible_history"]]
                if label == "SOURCE" else [row["target_text"]]
            )
            for index, quote in enumerate(value):
                if not isinstance(quote, str) or not quote.strip() or len(quote) > 300:
                    return original(position, row, response, model, revision)
                if any(quote in body for body in bodies):
                    continue
                replacement = reconcile_quote(quote, bodies)
                if replacement is None:
                    unmatched += 1
                    continue
                if updated is None:
                    updated = dict(response)
                    updated["specific_source_quotes"] = list(response["specific_source_quotes"])
                    updated["specific_target_quotes"] = list(response["specific_target_quotes"])
                updated[field][index] = replacement
                edits += 1
                emit("QUOTE_LITERAL_RECONCILED", position=position,
                     field=label, conservative=True, exact_source_backed=True)
        if unmatched:
            emit("QUOTE_RECONCILIATION_HOLD", position=position,
                 unresolved_count=min(unmatched, 25), repaired_count=edits)
            # Partial corrections are discarded: the entire original attempt
            # still fails the original validator.
            return original(position, row, response, model, revision)
        if updated is not None:
            emit("QUOTE_RECONCILIATION_CANDIDATE", position=position,
                 repaired_count=edits, nonquote_fields_unchanged=True)
        # No independent automatic quality admission; frozen validation applies
        # to the complete amended record and retains any non-quote violations.
        return original(position, row, updated if updated is not None else response,
                        model, revision)

    return observed
