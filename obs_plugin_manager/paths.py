"""XDG-style path resolution. Every path the app touches goes through here so
tests can redirect the whole app into a scratch directory via env vars,
without ever risking the user's real OBS install.
"""

import os
from pathlib import Path

from . import APP_NAME


def _xdg_dir(env_var: str, default_relative: str) -> Path:
    override = os.environ.get(env_var)
    base = Path(override) if override else Path.home() / default_relative
    return base / APP_NAME


def config_dir() -> Path:
    return _xdg_dir("XDG_CONFIG_HOME", ".config")


def cache_dir() -> Path:
    return _xdg_dir("XDG_CACHE_HOME", ".cache")


def data_dir() -> Path:
    return _xdg_dir("XDG_DATA_HOME", ".local/share")


def obs_config_dir() -> Path:
    override = os.environ.get("OBSPM_OBS_CONFIG_DIR")
    return Path(override) if override else Path.home() / ".config" / "obs-studio"


def obs_plugins_dir() -> Path:
    return obs_config_dir() / "plugins"


def obs_logs_dir() -> Path:
    return obs_config_dir() / "logs"


def backup_dir() -> Path:
    return data_dir() / "backups"


def scratch_dir() -> Path:
    return cache_dir() / "scratch"


def downloads_dir() -> Path:
    return cache_dir() / "downloads"


def config_file() -> Path:
    return config_dir() / "config.json"


def catalog_cache_file() -> Path:
    return cache_dir() / "catalog_cache.json"


def state_file() -> Path:
    return data_dir() / "state.json"


def ensure_dirs() -> None:
    for d in (config_dir(), cache_dir(), data_dir(), backup_dir(), scratch_dir(), downloads_dir()):
        d.mkdir(parents=True, exist_ok=True)
