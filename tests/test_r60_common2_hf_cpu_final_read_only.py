"""Synthetic final CPU2 preflight checks; no service calls."""
from __future__ import annotations

from types import SimpleNamespace

from scripts import r60_common2_hf_cpu_final_read_only as final_gate
from scripts import r60_common2_hf_cpu_image_retry as retry
from scripts import r60_common2_hf_cpu_stage as staging
from scripts import r60_common2_hf_cpu_stage_v2 as v2
from tests.test_r60_common2_hf_cpu_stage import fixture

KEY = "r60-common2-cpu2-20261112T090000Z-bbbbbbbbbbbb"


class FakeApi:
    def __init__(self, stage, jobs=(), output_files=()):
        self.stage = stage
        self.jobs = jobs
        self.output_files = output_files
        self.calls = []

    def list_bucket_tree(self, bucket, prefix, recursive):
        self.calls.append(("bucket", prefix))
        if "/runs/" in prefix:
            return [SimpleNamespace(path=prefix + p, type="file")
                    for p in sorted(final_gate.bucket.expected(self.stage))]
        return [SimpleNamespace(path=prefix + p, type="file") for p in self.output_files]

    def list_jobs(self, *, namespace):
        self.calls.append(("jobs", namespace))
        return list(self.jobs)


def create_stage(tmp_path):
    inp = fixture(tmp_path)
    old = tmp_path / retry.RUN_KEY
    staging.stage(inp, old, retry.RUN_KEY)
    new = tmp_path / KEY
    v2.build(old, new, KEY)
    return new


def test_completed_paginated_history_no_match(tmp_path, monkeypatch):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, jobs=[SimpleNamespace(name="other", labels={}) for _ in range(100)])
    monkeypatch.setattr(final_gate, "walk_job_history", lambda _api, _key: (125, 0))
    result = final_gate.check(api, stage, KEY)
    assert result["local_stage"] == "PASS"
    assert result["remote_input"] == "READY_PASS"
    assert result["remote_output"] == "EMPTY_PASS"
    assert result["submit_marker"] == "ABSENT"
    assert result["visible_jobs"] == 125
    assert result["status"] == "CPU2_HISTORY_PAGINATED_PASS__NO_JOB"
    assert result["reason_code"] == "JOB_HISTORY_EXHAUSTIVE_NO_MATCH"
    assert result["job_submission_calls"] == 0
    assert result["history_exhaustive"] is True


def test_output_nonempty_prevents_job_list(tmp_path):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, output_files=["receipt.json"])
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "OUTPUT_ALREADY_PRESENT"
    assert all(call[0] != "jobs" for call in api.calls)


def test_present_marker_short_circuits_all_remote_reads(tmp_path):
    stage = create_stage(tmp_path)
    (tmp_path / (KEY + ".cpu-submit-v2-attempted")).mkdir()
    api = FakeApi(stage)
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "SUBMISSION_ALREADY_ATTEMPTED"
    assert result["submit_marker"] == "PRESENT"
    assert api.calls == []


def test_named_existing_job_holds(tmp_path, monkeypatch):
    stage = create_stage(tmp_path)
    api = FakeApi(stage, jobs=[SimpleNamespace(name=KEY, labels={})])
    monkeypatch.setattr(final_gate, "walk_job_history", lambda _api, _key: (101, 1))
    result = final_gate.check(api, stage, KEY)
    assert result["reason_code"] == "PAGINATED_JOB_MATCH_HOLD"
    assert result["matching_jobs"] == 1
    assert result["job_submission_calls"] == 0

def test_walk_link_pagination_and_hidden_job(monkeypatch):
    import huggingface_hub
    key = KEY
    class Response:
        def __init__(self, entries, links):
            self.entries = entries
            self.links = links
        def raise_for_status(self):
            return None
        def json(self):
            return self.entries

    def job(i, key_match=False):
        return {"id": str(i), "name": "fixed-name", "labels": {},
                "environment": {"STORYFORGE_R60_COMMON2_RUN_KEY": key} if key_match else {}}
    pages = [
        Response([job(i) for i in range(100)],
                 {"next": {"url": "/api/jobs/adradar?cursor=page2"}}),
        Response([job(100, True)], {}),
    ]
    class FakeSession:
        def __init__(self):
            self.calls = []
        def get(self, url, **kwargs):
            self.calls.append(url)
            return pages[len(self.calls)-1]
    session = FakeSession()
    monkeypatch.setattr(huggingface_hub, "get_session", lambda: session)
    api = SimpleNamespace(
        endpoint="https://huggingface.co",
        _build_hf_headers=lambda: {"authorization": "Bearer private"},
    )
    count, matches = final_gate.walk_job_history(api, key)
    assert (count, matches) == (101, 1)
    assert session.calls == [
        "https://huggingface.co/api/jobs/adradar",
        "https://huggingface.co/api/jobs/adradar?cursor=page2",
    ]


def test_link_redirect_to_foreign_host_fails_closed(monkeypatch):
    import huggingface_hub
    from pytest import raises
    class Response:
        links = {"next": {"url": "https://evil.example/api/jobs/adradar"}}
        def raise_for_status(self):
            return None
        def json(self):
            return [{"id": "one"}]
    class Session:
        def get(self, url, **kwargs):
            assert url == "https://huggingface.co/api/jobs/adradar"
            return Response()
    monkeypatch.setattr(huggingface_hub, "get_session", lambda: Session())
    api = SimpleNamespace(
        endpoint="https://huggingface.co",
        _build_hf_headers=lambda: {"authorization": "Bearer private"},
    )
    with raises(ValueError, match="PAGINATION_URL_HOLD"):
        final_gate.walk_job_history(api, KEY)
