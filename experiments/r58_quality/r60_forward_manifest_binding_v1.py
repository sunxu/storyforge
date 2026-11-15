"""Ground require_pre_review()/Reviewer V2 in real on-disk manifests.

Problem this closes: require_pre_review() and execute_synthetic() previously
accepted caller-supplied protection/world dicts verbatim, so a boolean field
being True was never actually checked against a real file. This module loads
the frozen protection/world-component manifest files (0600, create-only,
single-link, size-bounded via r60_real_private_batch.read_private), verifies
their own internal content-hash has not drifted, and derives the
protection/world dicts strictly from that verified content before delegating
to the existing gate/ledger. No new Provider adapter, no scoring logic here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import r60_forward_evidence_gate_v1 as gate
import r60_forward_reviewer_v2_ledger as ledger
import r60_real_private_batch as private

PROTECTION_SCHEMA = "storyforge_r60_forward_eval_protection_manifest_v1"
WORLD_SCHEMA = "storyforge_r60_forward_world_components_v1"
MAX_MANIFEST_BYTES = 400_000


class Hold(ValueError):
    pass


def _self_hash(manifest: dict) -> str:
    return gate.sha({k: v for k, v in manifest.items() if k != "manifest_sha256"})


def _load_manifest(path: Path, schema: str) -> tuple[dict, str]:
    try:
        raw = private.read_private(path, MAX_MANIFEST_BYTES)
    except private.Hold as exc:
        raise Hold("MANIFEST_FILE_GUARD_HOLD") from exc
    file_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        manifest = json.loads(raw)
    except ValueError as exc:
        raise Hold("MANIFEST_JSON_HOLD") from exc
    if (type(manifest) is not dict or manifest.get("schema") != schema
            or not gate._digest(manifest.get("manifest_sha256"))
            or manifest["manifest_sha256"] != _self_hash(manifest)):
        raise Hold("MANIFEST_INTEGRITY_HOLD")
    return manifest, file_sha256


def load_protection_manifest(path: Path) -> tuple[dict, str]:
    return _load_manifest(path, PROTECTION_SCHEMA)


def load_world_manifest(path: Path) -> tuple[dict, str]:
    return _load_manifest(path, WORLD_SCHEMA)


def protection_for_case(manifest: dict, file_sha256: str, case_sha256: object) -> dict:
    if type(manifest) is not dict or manifest.get("schema") != PROTECTION_SCHEMA:
        raise Hold("PROTECTION_MANIFEST_SCHEMA_HOLD")
    return {
        "manifest_frozen": manifest.get("manifest_frozen") is True,
        "covers_all_protected_sets": manifest.get("covers_all_protected_sets") is True,
        "exact_identity_disjoint": manifest.get(
            "exact_identity_disjoint_vs_resolved_sets") is True,
        "semantic_overlap_cleared": manifest.get("semantic_overlap_cleared") is True,
        "manifest_sha256": file_sha256,
        "case_sha256": case_sha256,
    }


def world_for_case(manifest: dict, file_sha256: str, case_sha256: object) -> dict:
    if type(manifest) is not dict or manifest.get("schema") != WORLD_SCHEMA:
        raise Hold("WORLD_MANIFEST_SCHEMA_HOLD")
    components = manifest.get("components")
    if type(components) is not list:
        raise Hold("WORLD_MANIFEST_SHAPE_HOLD")
    matches = [c for c in components
               if type(c) is dict and c.get("case_sha256") == case_sha256]
    if len(matches) != 1:
        raise Hold("WORLD_COMPONENT_NOT_FOUND_HOLD")
    component = matches[0]
    raw_split = component.get("proposed_split")
    if (component.get("proposed_split_is_binding") is True
            and raw_split in ("train", "validation")):
        split_value = raw_split
    else:
        split_value = None
    return {
        "source_bound_roles_and_world": component.get(
            "exact_identity_isolation_verified") is True,
        "semantic_components_adjudicated": component.get(
            "semantic_components_adjudicated") is True,
        "all_uncertain_links_quarantined": component.get(
            "all_uncertain_links_quarantined") is True,
        "train_validation_component_disjoint": component.get(
            "train_validation_component_disjoint") is True,
        "case_sha256": case_sha256,
        "component_manifest_sha256": file_sha256,
        "component_key_private": component.get("component_key_private"),
        "split": split_value,
    }


def require_pre_review_from_manifests(
    *, source: dict, protection_manifest_path: Path, world_manifest_path: Path,
) -> dict:
    """Load+verify both manifests from disk; derive protection/world; delegate.

    Raises Hold on any manifest-guard failure before ever touching
    gate.require_pre_review; raises gate.Hold for any evidentiary gap the
    manifests themselves disclose (e.g. covers_all_protected_sets False).
    """
    case_sha256 = source.get("case_sha256") if type(source) is dict else None
    protection_manifest, protection_file_sha = load_protection_manifest(
        protection_manifest_path)
    world_manifest, world_file_sha = load_world_manifest(world_manifest_path)
    protection = protection_for_case(
        protection_manifest, protection_file_sha, case_sha256)
    world = world_for_case(world_manifest, world_file_sha, case_sha256)
    return gate.require_pre_review(source, protection, world)


def reject_duplicate_submission(registry_dir: Path, case_sha256: str) -> None:
    if type(case_sha256) is not str or not gate.DIGEST.fullmatch(case_sha256):
        raise Hold("CASE_SHA256_HOLD")
    marker = registry_dir / f"{case_sha256}.SEALED"
    if marker.exists() or marker.is_symlink():
        raise Hold("DUPLICATE_SEAL_SUBMISSION_HOLD")


def _mark_sealed(registry_dir: Path, case_sha256: str) -> None:
    marker = registry_dir / f"{case_sha256}.SEALED"
    private.write_new(marker, b"SEALED\n")


def execute_synthetic_from_manifests(
    *, output_dir: Path, seal_registry_dir: Path, source: dict,
    protection_manifest_path: Path, world_manifest_path: Path,
    case: dict, specs: list[dict], transport,
) -> dict:
    """Same two-side synthetic ledger as execute_synthetic(), but protection
    and world facts come from verified on-disk manifests, and a case that
    already holds a sealed marker in seal_registry_dir is refused outright.

    No new Provider adapter: this only derives trusted inputs and calls the
    existing r60_forward_reviewer_v2_ledger.execute_synthetic() unchanged.
    """
    case_sha256 = source.get("case_sha256") if type(source) is dict else None
    reject_duplicate_submission(seal_registry_dir, case_sha256)
    protection_manifest, protection_file_sha = load_protection_manifest(
        protection_manifest_path)
    world_manifest, world_file_sha = load_world_manifest(world_manifest_path)
    protection = protection_for_case(
        protection_manifest, protection_file_sha, case_sha256)
    world = world_for_case(world_manifest, world_file_sha, case_sha256)
    safe = ledger.execute_synthetic(
        output_dir=output_dir, source=source, protection=protection,
        world=world, case=case, specs=specs, transport=transport)
    _mark_sealed(seal_registry_dir, case_sha256)
    return safe
