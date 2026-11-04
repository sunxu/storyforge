"""Create-only SAFE JSON publication and real output capability probing."""

from __future__ import annotations

import errno
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
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
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
        except ValueError:
            raise
        except OSError as exc:
            raise ValueError("OUTPUT_PROBE_FAILED") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            if not cleaned:
                try:
                    current = path.lstat()
                    if fd >= -1 and stat.S_ISREG(current.st_mode):
                        path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass

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
        data = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        token = secrets.token_hex(12)
        temp_path = root / f".storyforge-tmp-{token}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("OUTPUT_CREATE_FAILED")
        flags |= os.O_NOFOLLOW
        fd = -1
        temp_identity: tuple[int, int] | None = None
        published_identity: tuple[int, int] | None = None
        published = False
        try:
            fd = os.open(temp_path, flags, mode)
            created = os.fstat(fd)
            temp_identity = (created.st_dev, created.st_ino)
            try:
                os.fchmod(fd, mode)
            except OSError as exc:
                raise ValueError("OUTPUT_VERIFY_FAILED") from exc
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                if written <= 0:
                    raise ValueError("OUTPUT_WRITE_FAILED")
                view = view[written:]
            try:
                os.fsync(fd)
            except OSError as exc:
                raise ValueError("OUTPUT_FSYNC_FAILED") from exc
            final = os.fstat(fd)
            actual_mode = stat.S_IMODE(final.st_mode)
            if (
                not stat.S_ISREG(final.st_mode)
                or final.st_size != len(data)
                or actual_mode != mode
            ):
                raise ValueError("OUTPUT_VERIFY_FAILED")
            # Hard-link publication is atomic and fails if the destination exists.
            try:
                os.link(temp_path, path, follow_symlinks=False)
            except FileExistsError as exc:
                raise ValueError("OUTPUT_ALREADY_EXISTS") from exc
            except OSError as exc:
                if exc.errno == errno.EEXIST:
                    raise ValueError("OUTPUT_ALREADY_EXISTS") from exc
                raise ValueError("OUTPUT_CREATE_FAILED") from exc
            published_stat = path.lstat()
            published_identity = (published_stat.st_dev, published_stat.st_ino)
            if published_identity != temp_identity:
                raise ValueError("OUTPUT_VERIFY_FAILED")
            temp_path.unlink()
            temp_identity = None
            dir_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(dir_fd)
            except OSError as exc:
                raise ValueError("OUTPUT_FSYNC_FAILED") from exc
            finally:
                os.close(dir_fd)
            published = True
            return WriteReceipt(len(data), hashlib.sha256(data).hexdigest(), actual_mode)
        except ValueError:
            raise
        except OSError as exc:
            raise ValueError("OUTPUT_WRITE_FAILED") from exc
        finally:
            if fd >= 0:
                os.close(fd)
            if temp_identity is not None:
                try:
                    current = temp_path.lstat()
                    if (current.st_dev, current.st_ino) == temp_identity:
                        temp_path.unlink()
                except OSError:
                    pass
            if not published and published_identity is not None:
                try:
                    current = path.lstat()
                    if (current.st_dev, current.st_ino) == published_identity:
                        path.unlink()
                except OSError:
                    pass
