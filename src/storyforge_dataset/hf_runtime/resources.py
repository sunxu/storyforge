"""CPU profile checks; never imports CUDA or changes execution mode."""

from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping
import os


@dataclass(frozen=True)
class ResourceReport:
    profile: str
    status: str
    error_code: str | None
    checks: dict[str, str]
    gpu_started: bool = False
    training_performed: bool = False

    def to_safe_dict(self) -> dict[str, object]:
        return asdict(self)


class ResourceGuard:
    @staticmethod
    def check_cpu_only(*, environ: Mapping[str, str] | None = None) -> ResourceReport:
        return ResourceGuard.check_profile("cpu", environ=environ)

    @staticmethod
    def check_profile(
        profile: str,
        *,
        environ: Mapping[str, str] | None = None,
    ) -> ResourceReport:
        if profile != "cpu":
            raise ValueError("RESOURCE_PROFILE_UNSUPPORTED")
        env = os.environ if environ is None else environ
        checks: dict[str, str] = {}
        cuda_visible = env.get("CUDA_VISIBLE_DEVICES")
        nvidia_visible = env.get("NVIDIA_VISIBLE_DEVICES")
        forbidden = {"none", "void", "-1"}
        if cuda_visible is not None and cuda_visible.strip().lower() not in {"", *forbidden}:
            checks["cuda_visibility"] = "FAIL"
            code = "CPU_PROFILE_GPU_VISIBLE"
        else:
            checks["cuda_visibility"] = "PASS"
            code = None
        if nvidia_visible is not None and nvidia_visible.strip().lower() not in {"", *forbidden}:
            checks["nvidia_visibility"] = "FAIL"
            code = "CPU_PROFILE_GPU_VISIBLE"
        else:
            checks["nvidia_visibility"] = "PASS"
        device_nodes = any(Path("/dev").glob("nvidia[0-9]*")) or any(
            (Path("/dev") / name).exists() for name in ("nvidiactl", "nvidia-uvm")
        )
        checks["nvidia_device_nodes"] = "FAIL" if device_nodes else "PASS"
        if device_nodes:
            code = "CPU_PROFILE_CUDA_DEVICE_DETECTED"
        # torch may be installed for unrelated CPU work; do not import it or
        # classify its mere presence as evidence of GPU execution.
        checks["runtime_no_cuda_import"] = "PASS" if "torch.cuda" not in sys.modules else "FAIL"
        if checks["runtime_no_cuda_import"] == "FAIL":
            code = "CPU_PROFILE_CUDA_DEVICE_DETECTED"
        status = "FAIL" if "FAIL" in checks.values() else "PASS"
        return ResourceReport(profile=profile, status=status, error_code=code, checks=checks)
