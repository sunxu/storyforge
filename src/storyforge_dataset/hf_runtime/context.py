"""Runtime environment identification without environment-dump leakage."""

from __future__ import annotations

import os
import platform
import sys
from collections.abc import Mapping
from dataclasses import asdict, dataclass

from . import __version__


@dataclass(frozen=True)
class RuntimeContext:
    runtime: str
    profile: str
    python_implementation: str
    python_version: str
    operating_system: str
    platform_machine: str
    container_hint: bool
    hf_job_hint: bool
    runtime_version: str = __version__

    @classmethod
    def detect(
        cls,
        *,
        profile: str = "cpu",
        environ: Mapping[str, str] | None = None,
    ) -> RuntimeContext:
        if profile not in {"cpu"}:
            raise ValueError("RUNTIME_PROFILE_INVALID")
        env = os.environ if environ is None else environ
        hf_hint = bool(env.get("JOB_ID") or env.get("HF_JOB_ID") or env.get("HF_JOB_NAME"))
        container_hint = os.path.exists("/.dockerenv") or bool(env.get("container"))
        runtime = "HF_JOB" if hf_hint else "CONTAINER" if container_hint else "LOCAL"
        if env.get("STORYFORGE_RUNTIME_TEST") == "1":
            runtime = "TEST"
        return cls(
            runtime=runtime,
            profile=profile,
            python_implementation=platform.python_implementation(),
            python_version=platform.python_version(),
            operating_system=sys.platform,
            platform_machine=platform.machine(),
            container_hint=container_hint,
            hf_job_hint=hf_hint,
        )

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)
