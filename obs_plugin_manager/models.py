"""Shared data shapes used across the app."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

Status = Literal[
    "up_to_date",
    "update_available",
    "not_installed",
    "installed_unmanaged",
    "not_available_linux",
    "unknown",
]


@dataclass
class CatalogEntry:
    name: str
    url: str
    version: str
    downloads: dict  # {"windows": str|None, "linux": str|None, "macOS": str|None}
    platforms: dict
    recommended: bool
    required: bool
    search_string: Optional[str]
    module_name: Optional[str]
    last_updated: Optional[str]

    @property
    def linux_download_url(self) -> Optional[str]:
        return (self.downloads or {}).get("linux") or None

    @classmethod
    def from_api(cls, raw: dict) -> "CatalogEntry":
        return cls(
            name=raw.get("name", ""),
            url=raw.get("url", ""),
            version=raw.get("version", ""),
            downloads=raw.get("downloads") or {},
            platforms=raw.get("platforms") or {},
            recommended=bool(raw.get("recommended", False)),
            required=bool(raw.get("required", False)),
            search_string=raw.get("searchString") or None,
            module_name=raw.get("moduleName") or None,
            last_updated=raw.get("lastUpdated") or None,
        )


@dataclass
class InstalledPlugin:
    folder_name: str
    folder_path: Path
    so_path: Path
    so_basename: str  # stem of the .so, e.g. "tuna"


@dataclass
class MatchResult:
    installed: Optional[InstalledPlugin]
    catalog_entry: Optional[CatalogEntry]


@dataclass
class ManagedRecord:
    plugin_folder_name: str
    module_name: Optional[str]
    catalog_name: str
    installed_version: str
    download_url_used: str
    install_date: str
    last_update_date: str
    files_written: list = field(default_factory=list)
    backup_path: Optional[str] = None

    def to_json(self) -> dict:
        return {
            "plugin_folder_name": self.plugin_folder_name,
            "module_name": self.module_name,
            "catalog_name": self.catalog_name,
            "installed_version": self.installed_version,
            "download_url_used": self.download_url_used,
            "install_date": self.install_date,
            "last_update_date": self.last_update_date,
            "files_written": self.files_written,
            "backup_path": self.backup_path,
        }

    @classmethod
    def from_json(cls, raw: dict) -> "ManagedRecord":
        return cls(
            plugin_folder_name=raw["plugin_folder_name"],
            module_name=raw.get("module_name"),
            catalog_name=raw.get("catalog_name", ""),
            installed_version=raw.get("installed_version", "unknown"),
            download_url_used=raw.get("download_url_used", ""),
            install_date=raw.get("install_date", ""),
            last_update_date=raw.get("last_update_date", ""),
            files_written=raw.get("files_written", []),
            backup_path=raw.get("backup_path"),
        )


@dataclass
class PluginRow:
    display_name: str
    installed_version: str  # "unknown" or a version string, or "" if not installed
    latest_version: str  # "" if no catalog entry
    status: Status
    catalog_entry: Optional[CatalogEntry]
    installed: Optional[InstalledPlugin]
    forum_url: str = ""
