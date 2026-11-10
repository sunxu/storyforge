"""Reusable, fail-closed StoryForge generation evaluation primitives."""

from .backend import (
    TransformersGenerationBackend,
    classify_finish_reason,
    download_pinned_tokenizer_snapshot,
    verify_tokenizer_snapshot,
)
from .plan import GenerationJobPlan, PlanError, build_generation_plan
from .profiles import ProfileAssessment, assess_profile, load_profile
from .worker import (
    GenerationBackend,
    GenerationResult,
    WorkerError,
    WorkerReceipt,
    run_generation_batch,
)

__all__ = [
    "GenerationBackend",
    "GenerationJobPlan",
    "GenerationResult",
    "PlanError",
    "ProfileAssessment",
    "TransformersGenerationBackend",
    "WorkerError",
    "WorkerReceipt",
    "assess_profile",
    "build_generation_plan",
    "classify_finish_reason",
    "download_pinned_tokenizer_snapshot",
    "load_profile",
    "run_generation_batch",
    "verify_tokenizer_snapshot",
]
