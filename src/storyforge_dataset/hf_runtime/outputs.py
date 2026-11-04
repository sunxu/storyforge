"""Create-only SAFE JSON publication and real output capability probing."""

from __future__ import annotations

import ctypes
import errno
import hashlib
import json
import os
import secrets
import stat
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


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
    def _rename_noreplace(source: Path, target: Path) -> None:
        """Atomically rename without replacing an existing target on Linux."""
        if not sys.platform.startswith("linux"):
            raise OSError(errno.EOPNOTSUPP, "atomic no-replace rename unavailable")
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(errno.EOPNOTSUPP, "renameat2 unavailable")
        renameat2.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100, os.fsencode(source), -100, os.fsencode(target), 1
        )  # AT_FDCWD, RENAME_NOREPLACE
        if result != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(target))

    @staticmethod
    def _check_root(root: Path) -> None:
        try:
            info = root.lstat()
        except OSError as exc:
            raise ValueError("OUTPUT_PARENT_INVALID") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("OUTPUT_PARENT_INVALID")

    @staticmethod
    def _unlink_if_identity(path: Path, identity: tuple[int, int]) -> bool:
        try:
            current = path.lstat()
        except FileNotFoundError:
            return True
        if (current.st_dev, current.st_ino) != identity:
            return False
        path.unlink()
        return True

    @classmethod
    def probe(cls, root: Path) -> OutputCapability:
        cls._check_root(root)
        path = root / f".storyforge-probe-{secrets.token_hex(12)}"
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("OUTPUT_PROBE_FAILED")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = -1
        identity: tuple[int, int] | None = None
        cleaned = False
        primary_error: ValueError | None = None
        try:
            fd = os.open(path, flags, 0o600)
            info = os.fstat(fd)
            identity = (info.st_dev, info.st_ino)
            os.fchmod(fd, 0o600)
            info = os.fstat(fd)
            if stat.S_IMODE(info.st_mode) != 0o600:
                raise ValueError("OUTPUT_VERIFY_FAILED")
            if os.write(fd, b"r60-probe") != len(b"r60-probe"):
                raise ValueError("OUTPUT_WRITE_FAILED")
            os.fsync(fd)
            os.close(fd)
            fd = -1
            current = path.lstat()
            if identity != (current.st_dev, current.st_ino):
                raise ValueError("OUTPUT_VERIFY_FAILED")
            path.unlink()
            cleaned = True
        except ValueError as exc:
            primary_error = exc
        except OSError:
            primary_error = ValueError("OUTPUT_PROBE_FAILED")
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    primary_error = ValueError("OUTPUT_CLEANUP_FAILED")
            if not cleaned and identity is not None:
                try:
                    cleaned = cls._unlink_if_identity(path, identity)
                except OSError:
                    primary_error = ValueError("OUTPUT_CLEANUP_FAILED")
                if not cleaned and primary_error is None:
                    primary_error = ValueError("OUTPUT_CLEANUP_FAILED")
        if primary_error is not None:
            raise primary_error
        return OutputCapability(True, stat.S_IMODE(root.stat().st_mode), cleaned)

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
        if mode != 0o600:
            raise ValueError("OUTPUT_VERIFY_FAILED")
        if path.is_symlink():
            raise ValueError("OUTPUT_SYMLINK_REJECTED")
        data = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        token = secrets.token_hex(12)
        temp_path = root / f".storyforge-tmp-{token}"
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError("OUTPUT_CREATE_FAILED")
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        fd = -1
        temp_identity: tuple[int, int] | None = None
        published_identity: tuple[int, int] | None = None
        published = False
        cleanup_failed = False
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
            if not stat.S_ISREG(final.st_mode) or final.st_size != len(data) or actual_mode != mode:
                raise ValueError("OUTPUT_VERIFY_FAILED")
            os.lseek(fd, 0, os.SEEK_SET)
            readback = bytearray()
            while len(readback) < len(data):
                chunk = os.read(fd, min(1024 * 1024, len(data) - len(readback)))
                if not chunk:
                    break
                readback.extend(chunk)
            if bytes(readback) != data:
                raise ValueError("OUTPUT_VERIFY_FAILED")
            try:
                os.link(temp_path, path, follow_symlinks=False)
            except FileExistsError as exc:
                raise ValueError("OUTPUT_ALREADY_EXISTS") from exc
            except OSError as link_error:
                if link_error.errno == errno.EEXIST:
                    raise ValueError("OUTPUT_ALREADY_EXISTS") from link_error
                unsupported_link = {
                    errno.EPERM, errno.EOPNOTSUPP, errno.ENOTSUP,
                    errno.EXDEV, errno.ENOSYS,
                }
                if link_error.errno not in unsupported_link:
                    raise ValueError("OUTPUT_CREATE_FAILED") from link_error
                try:
                    cls._rename_noreplace(temp_path, path)
                except FileExistsError as exc:
                    raise ValueError("OUTPUT_ALREADY_EXISTS") from exc
                except OSError as rename_error:
                    if rename_error.errno == errno.EEXIST:
                        raise ValueError("OUTPUT_ALREADY_EXISTS") from rename_error
                    unsupported_rename = {
                        errno.EPERM, errno.EOPNOTSUPP, errno.ENOTSUP,
                        errno.EXDEV, errno.ENOSYS, errno.EINVAL,
                    }
                    if rename_error.errno in unsupported_rename:
                        raise ValueError("OUTPUT_ATOMIC_PUBLISH_UNSUPPORTED") from rename_error
                    raise ValueError("OUTPUT_CREATE_FAILED") from rename_error
                temp_identity = None
            published_identity = (created.st_dev, created.st_ino)
            published_stat = path.lstat()
            if published_identity != (published_stat.st_dev, published_stat.st_ino):
                raise ValueError("OUTPUT_VERIFY_FAILED")
            if temp_identity is not None:
                temp_path.unlink()
                temp_identity = None
            try:
                dir_fd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            except OSError as exc:
                raise ValueError("OUTPUT_FSYNC_FAILED") from exc
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
                try:
                    os.close(fd)
                except OSError:
                    cleanup_failed = True
            if temp_identity is not None:
                try:
                    if not cls._unlink_if_identity(temp_path, temp_identity):
                        cleanup_failed = True
                except OSError:
                    cleanup_failed = True
            if not published and published_identity is not None:
                try:
                    if not cls._unlink_if_identity(path, published_identity):
                        cleanup_failed = True
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                raise ValueError("OUTPUT_CLEANUP_FAILED")
