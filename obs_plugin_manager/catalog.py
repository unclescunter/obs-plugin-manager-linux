"""Fetches the plugin catalog from the configured API, with a local on-disk
mirror so the app keeps working if the live fetch fails. The base URL is
config-driven so pointing at a future self-hosted mirror is a config change,
not a code change.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

from . import paths
from .models import CatalogEntry

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.streamup.tips"
REQUEST_TIMEOUT_SECONDS = 8


class CatalogUnavailableError(Exception):
    """Raised when the live fetch fails and no usable local cache exists."""


def _load_config() -> dict:
    cfg_file = paths.config_file()
    if cfg_file.exists():
        try:
            return json.loads(cfg_file.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read config at %s, using defaults", cfg_file)
    return {}


def get_base_url() -> str:
    return _load_config().get("catalog_base_url", DEFAULT_BASE_URL)


def _write_cache(raw_payload: dict, source_url: str) -> None:
    paths.ensure_dirs()
    cache = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_url": source_url,
        "plugins": raw_payload.get("plugins", []),
    }
    tmp_path = paths.catalog_cache_file().with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(cache, indent=2))
    tmp_path.replace(paths.catalog_cache_file())


def _read_cache() -> Optional[dict]:
    cache_file = paths.catalog_cache_file()
    if not cache_file.exists():
        return None
    try:
        return json.loads(cache_file.read_text())
    except (json.JSONDecodeError, OSError):
        logger.warning("Failed to read catalog cache at %s", cache_file)
        return None


def cache_metadata() -> Optional[dict]:
    """Returns {"fetched_at": ..., "source_url": ...} for the last-cached catalog, or None."""
    cache = _read_cache()
    if cache is None:
        return None
    return {"fetched_at": cache.get("fetched_at"), "source_url": cache.get("source_url")}


def fetch_catalog(force: bool = False) -> list:
    """Fetches the catalog live; falls back to the local mirror on any failure.
    Raises CatalogUnavailableError only if the live fetch fails AND no cache exists.
    """
    base_url = get_base_url()
    url = f"{base_url}/plugins"
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
        if "plugins" not in payload:
            raise ValueError("catalog response missing 'plugins' key")
        _write_cache(payload, url)
        return [CatalogEntry.from_api(raw) for raw in payload["plugins"]]
    except (requests.RequestException, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Live catalog fetch from %s failed: %s", url, exc)
        cache = _read_cache()
        if cache is not None:
            logger.info("Falling back to cached catalog from %s", cache.get("fetched_at"))
            return [CatalogEntry.from_api(raw) for raw in cache.get("plugins", [])]
        raise CatalogUnavailableError(
            f"Could not reach {url} and no local catalog cache exists"
        ) from exc
