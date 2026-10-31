"""Downloads and safely extracts plugin archives (.deb/.zip/.tar.*) into an
isolated scratch directory. Nothing extracted is ever executed, and every
member is validated to resolve inside the scratch dir before anything is
written, guarding against zip-slip / path traversal and unsafe symlinks.
"""

import logging
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)

DOWNLOAD_CHUNK_SIZE = 1 << 16  # 64 KiB
DOWNLOAD_TIMEOUT_SECONDS = 30


class ArchiveSecurityError(Exception):
    """Raised when an archive member would escape the extraction directory."""


class UnsupportedArchiveError(Exception):
    """Raised when the downloaded file isn't a format this tool can handle."""


ProgressCallback = Optional[Callable[[int, int], None]]


def download(url: str, dest_path: Path, progress_cb: ProgressCallback = None) -> Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        written = 0
        with open(tmp_path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                if not chunk:
                    continue
                fh.write(chunk)
                written += len(chunk)
                if progress_cb is not None:
                    progress_cb(written, total)
    tmp_path.replace(dest_path)
    return dest_path


def _is_within_directory(base: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _safe_extract_tar(tar_path: Path, dest_dir: Path) -> None:
    with tarfile.open(tar_path) as tf:
        members = tf.getmembers()
        for member in members:
            member_path = dest_dir / member.name
            if not _is_within_directory(dest_dir, member_path):
                raise ArchiveSecurityError(f"path traversal attempt: {member.name}")
            if member.issym() or member.islnk():
                link_target = (
                    Path(member.linkname)
                    if Path(member.linkname).is_absolute()
                    else dest_dir / member.linkname
                )
                if not _is_within_directory(dest_dir, link_target):
                    raise ArchiveSecurityError(
                        f"unsafe symlink: {member.name} -> {member.linkname}"
                    )
            member.mode &= ~0o111  # nothing from an archive should be executable
        tf.extractall(dest_dir, members=members, filter="data")


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            member_path = dest_dir / info.filename
            if not _is_within_directory(dest_dir, member_path):
                raise ArchiveSecurityError(f"path traversal attempt: {info.filename}")
        zf.extractall(dest_dir)


def _extract_deb(deb_path: Path, job_dir: Path) -> Path:
    ar_dir = job_dir / "_ar"
    ar_dir.mkdir(parents=True, exist_ok=True)

    list_result = subprocess.run(
        ["ar", "t", str(deb_path.resolve())],
        capture_output=True,
        text=True,
        check=True,
    )
    members = [line.strip() for line in list_result.stdout.splitlines() if line.strip()]
    data_members = [m for m in members if m.startswith("data.tar")]
    if not data_members:
        raise UnsupportedArchiveError(f"no data.tar.* member found in {deb_path.name}: {members}")
    data_member = data_members[0]

    subprocess.run(
        ["ar", "x", str(deb_path.resolve()), data_member],
        cwd=ar_dir,
        check=True,
    )

    data_tar_path = ar_dir / data_member
    data_root = job_dir / "data_root"
    data_root.mkdir(parents=True, exist_ok=True)

    if data_tar_path.suffix == ".zst":
        decompressed = ar_dir / data_tar_path.stem  # strips .zst, leaves data.tar
        subprocess.run(
            ["zstd", "-d", "-f", str(data_tar_path), "-o", str(decompressed)],
            check=True,
        )
        _safe_extract_tar(decompressed, data_root)
    else:
        _safe_extract_tar(data_tar_path, data_root)

    return data_root


def extract_to_scratch(archive_path: Path, scratch_root: Path) -> Path:
    job_dir = scratch_root / uuid4().hex
    job_dir.mkdir(parents=True, exist_ok=True)

    if archive_path.suffix == ".deb":
        return _extract_deb(archive_path, job_dir)

    extract_dir = job_dir / "extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)

    if tarfile.is_tarfile(archive_path):
        _safe_extract_tar(archive_path, extract_dir)
    elif zipfile.is_zipfile(archive_path):
        _safe_extract_zip(archive_path, extract_dir)
    else:
        raise UnsupportedArchiveError(f"unrecognized archive format: {archive_path}")

    return extract_dir


def cleanup_scratch_job(extracted_dir: Path) -> None:
    """Removes an entire per-job scratch directory (the uuid4-named parent of
    whatever extract_to_scratch returned)."""
    # extract_to_scratch returns either job_dir/"data_root" or job_dir/"extracted";
    # walk up one level to remove the whole per-job directory, not just the subdir.
    job_dir = extracted_dir.parent
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
