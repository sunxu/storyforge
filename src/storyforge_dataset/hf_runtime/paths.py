"""Explicit host/container path representation and Runner module bootstrap."""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal


@dataclass(frozen=True)
class ResolvedPath:
    kind: Literal["host", "container"]
    value: Path | PurePosixPath


class PathResolver:
    @staticmethod
    def resolve(
        path: str | Path,
        *,
        kind: Literal["host", "container", "auto"],
    ) -> ResolvedPath:
        raw = os.fspath(path)
        if not raw or "\x00" in raw:
            raise ValueError("PATH_NOT_ABSOLUTE")
        if kind == "auto":
            raise ValueError("PATH_KIND_AMBIGUOUS")
        if kind == "container":
            value = PurePosixPath(raw)
            if not value.is_absolute():
                raise ValueError("PATH_NOT_ABSOLUTE")
            if ".." in value.parts:
                raise ValueError("PATH_TRAVERSAL_REJECTED")
            return ResolvedPath(kind="container", value=value)
        if kind != "host":
            raise ValueError("PATH_KIND_AMBIGUOUS")
        value = Path(raw)
        if not value.is_absolute():
            raise ValueError("PATH_NOT_ABSOLUTE")
        if ".." in value.parts:
            raise ValueError("PATH_TRAVERSAL_REJECTED")
        return ResolvedPath(kind="host", value=value)

    @staticmethod
    def bootstrap_module_root(path: Path) -> Path:
        """Explicitly add a verified source root containing storyforge_dataset."""
        if not path.is_absolute() or ".." in path.parts:
            raise ValueError("PATH_NOT_ABSOLUTE")
        try:
            root_info = path.lstat()
            package = path / "storyforge_dataset"
            package_info = package.lstat()
            init_info = (package / "__init__.py").lstat()
        except OSError as exc:
            raise ValueError("PATH_NOT_FOUND") from exc
        if (
            not stat.S_ISDIR(root_info.st_mode)
            or not stat.S_ISDIR(package_info.st_mode)
            or not stat.S_ISREG(init_info.st_mode)
            or path.is_symlink()
            or package.is_symlink()
            or (package / "__init__.py").is_symlink()
        ):
            raise ValueError("PATH_TYPE_INVALID")
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
        return path

    @staticmethod
    def _validate_root(path: Path) -> Path:
        if not path.is_absolute():
            raise ValueError("PATH_NOT_ABSOLUTE")
        if ".." in path.parts:
            raise ValueError("PATH_TRAVERSAL_REJECTED")
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current = current / part
            try:
                if current.is_symlink():
                    raise ValueError("PATH_SYMLINK_REJECTED")
            except OSError as exc:
                raise ValueError("PATH_NOT_FOUND") from exc
        if not path.exists():
            raise ValueError("PATH_NOT_FOUND")
        if not path.is_dir():
            raise ValueError("PATH_TYPE_INVALID")
        return path

    @classmethod
    def validate_input_root(cls, path: Path) -> Path:
        return cls._validate_root(path)

    @classmethod
    def validate_output_root(cls, path: Path) -> Path:
        return cls._validate_root(path)
