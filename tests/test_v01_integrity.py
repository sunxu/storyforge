"""Protect the v0.1 evidence chain from silent changes on future main commits."""
from scripts.audit_v01_integrity import run


def test_v01_evidence_integrity() -> None:
    audit = run()
    assert audit["status"] == "V01_LOCAL_EVIDENCE_INTEGRITY_PASS__EXTERNAL_LIMITS_RETAINED"
    checks = audit["checks"]
    assert checks["dataset"]["status"] == "PASS"
    assert checks["dataset"]["split_counts"] == {"train": 65, "validation": 15, "test": 20}
    assert checks["heldout"]["test_alignment"] == "20/20"
    assert checks["checkpoint"]["file_count"] == 10
    assert checks["checkpoint"]["actual_remote_checkpoint_bytes_rehashed_by_ci"] is False
    assert checks["evaluation"]["validation"]["votes"] == {
        "base": 28, "adapter": 30, "tie": 2
    }
    assert checks["evaluation"]["gold"]["reviewer_independence"] == "NOT_VERIFIED"
    assert checks["decision"] == "ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED"
