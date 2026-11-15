"""Synthetic-only tests for manifest-grounded pre-review binding.

No network, no real Story content, no DB. Every manifest here is fabricated
in a temp private dir; "tampering" means hand-editing the written JSON bytes.
"""
import json

import pytest
import r60_forward_evidence_gate_v1 as gate
import r60_forward_manifest_binding_v1 as binding
import r60_real_private_batch as private
from test_r60_forward_evidence_gate_v1 import H, source
from test_r60_forward_reviewer_v2_ledger import case, response, specs


def protection_manifest(**overrides):
    body = {
        "schema": binding.PROTECTION_SCHEMA,
        "manifest_frozen": True,
        "covers_all_protected_sets": True,
        "exact_identity_disjoint_vs_resolved_sets": True,
        "semantic_overlap_cleared": True,
        "train_admitted": 0,
    }
    body.update(overrides)
    body["manifest_sha256"] = binding._self_hash(body)
    return body


def world_manifest(*, component_case_sha256=H, **component_overrides):
    component = {
        "case_sha256": component_case_sha256,
        "component_key_private": "synthetic-component-1",
        "exact_identity_isolation_verified": True,
        "semantic_components_adjudicated": True,
        "all_uncertain_links_quarantined": True,
        "train_validation_component_disjoint": True,
        "proposed_split": "train",
        "proposed_split_is_binding": True,
    }
    component.update(component_overrides)
    body = {
        "schema": binding.WORLD_SCHEMA,
        "components": [component],
        "train_admitted": 0,
    }
    body["manifest_sha256"] = binding._self_hash(body)
    return body


def write_manifest(root, name, body):
    path = root / name
    private.write_new(path, (json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n").encode())
    return path


def setup_root(monkeypatch, tmp_path):
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    monkeypatch.setattr(private, "BASE", root)
    return root


def test_happy_path_seal_from_manifests(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(root, "WORLD.json", world_manifest())
    seal = binding.require_pre_review_from_manifests(
        source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)
    assert seal["pre_review_seal_sha256"]
    assert seal["case_sha256"] == H


def test_tampered_manifest_rejected(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(root, "WORLD.json", world_manifest())
    tampered = json.loads(p_path.read_text())
    tampered["covers_all_protected_sets"] = False
    p_path.chmod(0o600)
    p_path.write_bytes((json.dumps(tampered, sort_keys=True, ensure_ascii=False) + "\n").encode())
    with pytest.raises(binding.Hold, match="MANIFEST_INTEGRITY_HOLD"):
        binding.require_pre_review_from_manifests(
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)


def test_missing_protection_coverage_holds(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json",
                             protection_manifest(covers_all_protected_sets=False))
    w_path = write_manifest(root, "WORLD.json", world_manifest())
    with pytest.raises(gate.Hold, match="EVALUATION_PROTECTION_HOLD"):
        binding.require_pre_review_from_manifests(
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)


def test_undecided_semantic_link_holds(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(
        root, "WORLD.json", world_manifest(semantic_components_adjudicated=False))
    with pytest.raises(gate.Hold, match="WORLD_COMPONENT_HOLD"):
        binding.require_pre_review_from_manifests(
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)


def test_wrong_split_holds(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(
        root, "WORLD.json",
        world_manifest(proposed_split="both", proposed_split_is_binding=True))
    with pytest.raises(gate.Hold, match="WORLD_COMPONENT_HOLD"):
        binding.require_pre_review_from_manifests(
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)


def test_component_not_found_holds(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(
        root, "WORLD.json", world_manifest(component_case_sha256="b" * 64))
    with pytest.raises(binding.Hold, match="WORLD_COMPONENT_NOT_FOUND_HOLD"):
        binding.require_pre_review_from_manifests(
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path)


def test_duplicate_submission_holds(monkeypatch, tmp_path):
    root = setup_root(monkeypatch, tmp_path)
    p_path = write_manifest(root, "PROTECTION.json", protection_manifest())
    w_path = write_manifest(root, "WORLD.json", world_manifest())
    registry = root / "seal-registry"
    registry.mkdir(mode=0o700)
    calls = []

    def fake_transport(side, body):
        calls.append(side)
        result = response()
        result["provider_request_id"] = "synthetic-" + side + "-0001"
        return result

    first = binding.execute_synthetic_from_manifests(
        output_dir=root / "ledger-run-1", seal_registry_dir=registry,
        source=source(), protection_manifest_path=p_path, world_manifest_path=w_path,
        case=case(), specs=specs(), transport=fake_transport)
    assert first["train_admitted"] == 0
    assert calls == ["a", "b"]

    with pytest.raises(binding.Hold, match="DUPLICATE_SEAL_SUBMISSION_HOLD"):
        binding.execute_synthetic_from_manifests(
            output_dir=root / "ledger-run-2", seal_registry_dir=registry,
            source=source(), protection_manifest_path=p_path, world_manifest_path=w_path,
            case=case(), specs=specs(), transport=fake_transport)
    assert calls == ["a", "b"]
