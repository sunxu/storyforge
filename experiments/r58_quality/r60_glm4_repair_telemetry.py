"""R60 GLM SAFE telemetry for bounded literal-quote repair pilots.

No raw model text, quotes or source identifiers. Telemetry is observational:
never modifies checkpoint outcomes or turns technical failures into quality HOLD.
"""
from __future__ import annotations

from collections import Counter

EVENTS = frozenset({
    "QUOTE_RECONCILIATION_HOLD",
    "QUOTE_RECONCILIATION_CANDIDATE",
    "QUOTE_LITERAL_REPAIR_INSTALLED",
})


class RepairTelemetry:
    def __init__(self, emit):
        self.emit = emit
        self.counters = Counter()
        self.positions = set()
        self.candidate_positions = set()
        self.unresolved_positions = set()

    def record(self, event: str, **data):
        if event not in EVENTS:
            raise ValueError("REPAIR_TELEMETRY_EVENT_HOLD")
        if event == "QUOTE_RECONCILIATION_CANDIDATE":
            pos = data["position"]
            self.candidate_positions.add(pos)
            self.counters["candidate_quotes"] += data["repaired_count"]
            self.counters["candidate_source_quotes"] += data["source_repairs"]
            self.counters["candidate_target_quotes"] += data["target_repairs"]
            self.positions.add(pos)
        elif event == "QUOTE_RECONCILIATION_HOLD":
            pos = data["position"]
            self.unresolved_positions.add(pos)
            self.positions.add(pos)
            self.counters["unresolved_quotes"] += data["unresolved_count"]
        self.emit(event, **data)

    def summarize(self, attempted: int, verified: int, failures: int) -> None:
        if not (0 <= verified + failures <= attempted <= 12):
            raise ValueError("REPAIR_TELEMETRY_COUNTS_HOLD")
        self.emit(
            "QUOTE_REPAIR_PILOT_SAFE_SUMMARY",
            attempted=attempted,
            verified=verified,
            technical_failures=failures,
            repair_candidate_cases=len(self.candidate_positions),
            unresolved_quote_cases=len(self.unresolved_positions),
            candidate_quotes=self.counters["candidate_quotes"],
            candidate_source_quotes=self.counters["candidate_source_quotes"],
            candidate_target_quotes=self.counters["candidate_target_quotes"],
            unresolved_quotes=self.counters["unresolved_quotes"],
            # Only a checkpoint from the original frozen reviewer is verified.
            quality_pass_count_not_inferred=True,
        )
