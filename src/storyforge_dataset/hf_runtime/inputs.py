"""Bounded, no-follow input reads with descriptor identity and SHA256 checks."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VerifiedInput:
    path_name: str
    size_bytes: int
    sha256: str
    _data: bytes

    def read_bytes(self) -> bytes:
        return self._data

    def to_safe_dict(self) -> dict[str, object]:
        return {"size_bytes": self.size_bytes, "sha256": self.sha256}


class InputManager:
    @staticmethod
    def open_verified(
        path: Path,
        *,
        max_bytes: int,
        expected_sha256: str | None = None,
        require_regular: bool = True,
    ) -> VerifiedInput:
        if max_bytes < 0:
            raise ValueError("INPUT_SIZE_LIMIT_EXCEEDED")
        flags = os.O_RDONLY
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("INPUT_SYMLINK_REJECTED")
        flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise ValueError("INPUT_SYMLINK_REJECTED") from exc
            raise ValueError("INPUT_OPEN_FAILED") from exc

        try:
            before = os.fstat(fd)
            if require_regular and not stat.S_ISREG(before.st_mode):
                raise ValueError("INPUT_NOT_REGULAR_FILE")
            if before.st_size > max_bytes:
                raise ValueError("INPUT_SIZE_LIMIT_EXCEEDED")
            chunks: list[bytes] = []
            digest = hashlib.sha256()
            total = 0
            while True:
                chunk = os.read(fd, min(1024 * 1024, max_bytes - total + 1))
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("INPUT_SIZE_LIMIT_EXCEEDED")
                digest.update(chunk)
                chunks.append(chunk)
            after = os.fstat(fd)
            identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
            identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            if identity_before != identity_after or total != after.st_size:
                raise ValueError("INPUT_DESCRIPTOR_CHANGED")
            actual = digest.hexdigest()
            if expected_sha256 is not None and actual != expected_sha256:
                raise ValueError("INPUT_SHA256_MISMATCH")
            return VerifiedInput(
                path_name=path.name,
                size_bytes=total,
                sha256=actual,
                _data=b"".join(chunks),
            )
        except ValueError:
            raise
        except OSError as exc:
            raise ValueError("INPUT_READ_FAILED") from exc
        finally:
            os.close(fd)
