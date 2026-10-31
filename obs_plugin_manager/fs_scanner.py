"""Enumerates the real (or scratch, in tests) OBS plugins directory."""

from pathlib import Path
from typing import Optional

from . import paths
from .models import InstalledPlugin


def scan_installed_plugins(plugins_dir: Optional[Path] = None) -> list:
    plugins_dir = plugins_dir if plugins_dir is not None else paths.obs_plugins_dir()
    if not plugins_dir.is_dir():
        return []

    results = []
    for folder in sorted(p for p in plugins_dir.iterdir() if p.is_dir()):
        bin64 = folder / "bin" / "64bit"
        if not bin64.is_dir():
            continue
        so_files = sorted(bin64.glob("*.so"))
        if not so_files:
            continue
        so_path = so_files[0]
        results.append(
            InstalledPlugin(
                folder_name=folder.name,
                folder_path=folder,
                so_path=so_path,
                so_basename=so_path.stem,
            )
        )
    return results
