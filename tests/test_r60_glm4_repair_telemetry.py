"""R60 CPU-only SAFE telemetry without private quote values."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] /
          "experiments/r58_quality/r60_glm4_repair_telemetry.py")
spec = importlib.util.spec_from_file_location("r60_glm4_repair_telemetry", SOURCE)
assert spec and spec.loader
telemetry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(telemetry)


def test_counts_repaired_and_unresolved_separate_from_quality():
    events = []
    reporter = telemetry.RepairTelemetry(
        lambda event, **fields: events.append((event, fields)))
    reporter.record("QUOTE_RECONCILIATION_CANDIDATE",
                    position=1, repaired_count=2,
                    source_repairs=1, target_repairs=1,
                    nonquote_fields_unchanged=True)
    reporter.record("QUOTE_RECONCILIATION_HOLD",
                    position=2, unresolved_count=3, repaired_count=1)
    reporter.summarize(attempted=2, verified=0, failures=2)
    event, result = events[-1]
    assert event == "QUOTE_REPAIR_PILOT_SAFE_SUMMARY"
    assert result["attempted"] == 2
    assert result["technical_failures"] == 2
    assert result["repair_candidate_cases"] == 1
    assert result["unresolved_quote_cases"] == 1
    assert result["candidate_quotes"] == 2
    assert result["candidate_source_quotes"] == 1
    assert result["candidate_target_quotes"] == 1
    assert result["unresolved_quotes"] == 3
    assert result["quality_pass_count_not_inferred"]
    assert "quote_text" not in str(events)


def test_unknown_event_cannot_emit_private_arguments():
    events = []
    reporter = telemetry.RepairTelemetry(
        lambda event, **fields: events.append((event, fields)))
    with pytest.raises(ValueError, match="REPAIR_TELEMETRY_EVENT_HOLD"):
        reporter.record("PRIVATE_DATA", original_quote="secret")
    assert not events


def test_invalid_attempt_counts_fail_closed():
    reporter = telemetry.RepairTelemetry(lambda *args, **kwargs: None)
    with pytest.raises(ValueError, match="REPAIR_TELEMETRY_COUNTS_HOLD"):
        reporter.summarize(attempted=2, verified=2, failures=1)
