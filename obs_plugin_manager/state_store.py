"""Atomic JSON read/write of the managed-install ledger: which plugins this
tool has installed/updated, what version, and what files it wrote (so a
future clean uninstall only removes what this tool actually put there).
"""

import json
from dataclasses import dataclass, field
from typing import Dict

from . import paths
from .models import ManagedRecord

SCHEMA_VERSION = 1


@dataclass
class AppState:
    schema_version: int = SCHEMA_VERSION
    managed_plugins: Dict[str, ManagedRecord] = field(default_factory=dict)

    def to_json(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "managed_plugins": {
                key: record.to_json() for key, record in self.managed_plugins.items()
            },
        }

    @classmethod
    def from_json(cls, raw: dict) -> "AppState":
        managed = {
            key: ManagedRecord.from_json(value)
            for key, value in raw.get("managed_plugins", {}).items()
        }
        return cls(schema_version=raw.get("schema_version", SCHEMA_VERSION), managed_plugins=managed)


def load() -> AppState:
    state_file = paths.state_file()
    if not state_file.exists():
        return AppState()
    try:
        return AppState.from_json(json.loads(state_file.read_text()))
    except (json.JSONDecodeError, OSError):
        return AppState()


def save(state: AppState) -> None:
    paths.ensure_dirs()
    state_file = paths.state_file()
    tmp_path = state_file.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(state.to_json(), indent=2))
    tmp_path.replace(state_file)


def record_install(record: ManagedRecord) -> None:
    state = load()
    state.managed_plugins[record.plugin_folder_name] = record
    save(state)
