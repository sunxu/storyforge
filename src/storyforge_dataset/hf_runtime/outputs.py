"""Create-only SAFE JSON publication and real output capability probing."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class OutputCapability:
    writable: bool
    directory_mode: int | None
    probe_cleaned: bool


@dataclass(frozen=True)
class WriteReceipt:
    size_bytes: int
    sha256: str
    mode: int


class OutputManager:
    @staticmethod
    def _check_root(root: Path) -> None:
        try:
            info = root.lstat()
        except OSError as exc:
            raise ValueError("OUTPUT_PARENT_INVALID") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("OUTPUT_PARENT_INVALID")

    @classmethod
    def probe(cls, root: Path) -> OutputCapability:
        cls._check_root(root)
        name = f".storyforge-probe-{secrets.token_hex(12)}"
        path = root / name
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = -1
        cleaned = False
        try:
            fd = os.open(path, flags, 0o600)
            os.write(fd, b"r60-probe")
            os.fsync(fd)
            info = os.fstat(fd)
            os.close(fd)
            fd = -1
            current = path.lstat()
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise ValueError("OUTPUT_VERIFY_FAILED")
            path.unlink()
            cleaned = True
            return OutputCapability(True, stat.S_IMODE(root.stat().st_mode), cleaned)
        except OSError as exc:
            raise ValueError("OUTPUT_PROBE_FAILED") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            if path.exists() and not path.is_symlink():
                try:
                    path.unlink()
                    cleaned = True
                except OSError:
                    cleaned = False

    @classmethod
    def write_safe(
        cls,
        path: Path,
        payload: Mapping[str, object],
        *,
        mode: int = 0o600,
    ) -> WriteReceipt:
        root = path.parent
        cls._check_root(root)
        if path.is_symlink():
            raise ValueError("OUTPUT_SYMLINK_REJECTED")
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = -1
        created_identity: tuple[int, int] | None = None
        try:
            fd = os.open(path, flags, mode)
            created = os.fstat(fd)
            created_identity = (created.st_dev, created.st_ino)
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise ValueError("OUTPUT_WRITE_FAILED")
                view = view[written:]
            os.fsync(fd)
            final = os.fstat(fd)
            if not stat.S_ISREG(final.st_mode) or final.st_size != len(data):
                raise ValueError("OUTPUT_VERIFY_FAILED")
            return WriteReceipt(len(data), hashlib.sha256(data).hexdigest(), stat.S_IMODE(final.st_mode))
        except FileExistsError as exc:
            raise ValueError("OUTPUT_ALREADY_EXISTS") from exc
        except ValueError:
            raise
        except OSError as exc:
            raise ValueError("OUTPUT_WRITE_FAILED") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            if created_identity is not None:
                try:
                    current = path.lstat()
                    if (current.st_dev, current.st_ino) == created_identity and current.st_size == 0:
                        path.unlink()
                except OSError:
                    pass
