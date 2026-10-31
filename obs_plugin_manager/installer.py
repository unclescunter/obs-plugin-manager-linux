"""Orchestrates a full install or update: download -> extract to scratch ->
classify/remap -> validate -> back up any existing real folder -> move into
place -> record state. Everything up to validation happens entirely inside a
scratch directory; the real OBS plugins directory is only ever touched after
the new content has been proven correct.
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

from . import archive, paths, remapper, state_store
from .matcher import slugify
from .models import CatalogEntry, InstalledPlugin, ManagedRecord

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[str], None]]


class InstallError(Exception):
    pass


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _dest_folder_name(entry: CatalogEntry, existing: Optional[InstalledPlugin]) -> str:
    if existing is not None:
        return existing.folder_name
    return entry.module_name or slugify(entry.name)


def _relative_files(root: Path) -> list:
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]


def _place_into_real_plugins_dir(built_plugin_dir: Path, folder_name: str) -> Optional[Path]:
    real_dest = paths.obs_plugins_dir() / folder_name
    paths.obs_plugins_dir().mkdir(parents=True, exist_ok=True)
    backup_path = None
    if real_dest.exists():
        paths.backup_dir().mkdir(parents=True, exist_ok=True)
        backup_path = paths.backup_dir() / f"{folder_name}__{_utc_now_compact()}"
        shutil.move(str(real_dest), backup_path)
    try:
        shutil.move(str(built_plugin_dir), real_dest)
    except Exception:
        if backup_path is not None:
            shutil.move(str(backup_path), real_dest)
        raise
    return backup_path


def install_or_update(
    entry: CatalogEntry,
    existing: Optional[InstalledPlugin] = None,
    progress_cb: ProgressCallback = None,
) -> ManagedRecord:
    def report(message: str) -> None:
        logger.info(message)
        if progress_cb is not None:
            progress_cb(message)

    url = entry.linux_download_url
    if not url:
        raise InstallError(f"{entry.name} has no Linux download available")

    paths.ensure_dirs()
    folder_name = _dest_folder_name(entry, existing)

    filename = Path(urlparse(url).path).name or f"{folder_name}-download"
    download_path = paths.downloads_dir() / filename

    report(f"Downloading {entry.name}...")
    archive.download(url, download_path)

    report("Extracting...")
    extracted_root = archive.extract_to_scratch(download_path, paths.scratch_dir())

    try:
        report("Preparing plugin files...")
        shape = remapper.classify_tree(extracted_root)
        built_plugin_dir = extracted_root.parent / "built"
        remapper.remap_to_plugin_layout(extracted_root, shape, built_plugin_dir)
        remapper.validate_plugin_layout(built_plugin_dir)

        report("Installing into OBS plugins directory...")
        backup_path = _place_into_real_plugins_dir(built_plugin_dir, folder_name)

        real_dest = paths.obs_plugins_dir() / folder_name
        now = _utc_now_iso()
        record = ManagedRecord(
            plugin_folder_name=folder_name,
            module_name=entry.module_name,
            catalog_name=entry.name,
            installed_version=entry.version,
            download_url_used=url,
            install_date=now if existing is None else _existing_install_date(folder_name, now),
            last_update_date=now,
            files_written=_relative_files(real_dest),
            backup_path=str(backup_path) if backup_path else None,
        )
        state_store.record_install(record)
        report(f"{entry.name} {entry.version} installed.")
        return record
    finally:
        archive.cleanup_scratch_job(extracted_root)


def _existing_install_date(folder_name: str, fallback: str) -> str:
    state = state_store.load()
    existing_record = state.managed_plugins.get(folder_name)
    return existing_record.install_date if existing_record else fallback
