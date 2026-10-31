"""Matches on-disk installed plugin folders to catalog entries.

Folder name, .so basename, and the catalog's moduleName/name can all disagree
in case (e.g. the real `Tuna` folder contains `tuna.so`, matching catalog
moduleName "tuna"), so every comparison here is lowercased. Matching is
deliberately conservative: a plugin that isn't a confident match stays
unmatched ("installed_unmanaged") rather than being guessed at.
"""

import difflib
import re
from typing import Optional

from .models import CatalogEntry, InstalledPlugin, MatchResult

FUZZY_THRESHOLD = 0.92

_SLUG_STRIP_SUFFIXES = (
    " for obs studio",
    " for obs",
    " plugin",
)


def slugify(name: str) -> str:
    lowered = name.lower()
    for suffix in _SLUG_STRIP_SUFFIXES:
        if lowered.endswith(suffix):
            lowered = lowered[: -len(suffix)]
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def _fuzzy_fallback(keys: list, catalog: list) -> Optional[CatalogEntry]:
    best_entry = None
    best_ratio = 0.0
    for entry in catalog:
        slug = slugify(entry.name)
        for key in keys:
            ratio = difflib.SequenceMatcher(None, key, slug).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_entry = entry
    return best_entry if best_ratio >= FUZZY_THRESHOLD else None


def match(installed: list, catalog: list) -> list:
    by_module_name = {
        entry.module_name.lower(): entry for entry in catalog if entry.module_name
    }
    by_name_slug = {slugify(entry.name): entry for entry in catalog if entry.name}

    results = []
    for plugin in installed:
        so_key = plugin.so_basename.lower()
        folder_key = plugin.folder_name.lower()

        entry = (
            by_module_name.get(so_key)
            or by_module_name.get(folder_key)
            or by_name_slug.get(so_key)
            or by_name_slug.get(folder_key)
            or _fuzzy_fallback([so_key, folder_key], catalog)
        )
        results.append(MatchResult(installed=plugin, catalog_entry=entry))
    return results


def unmatched_catalog_entries(installed: list, catalog: list) -> list:
    """Catalog entries with no corresponding installed plugin at all (candidates
    for a "Not installed" row)."""
    matched_results = match(installed, catalog)
    matched_entry_names = {
        id(r.catalog_entry) for r in matched_results if r.catalog_entry is not None
    }
    return [entry for entry in catalog if id(entry) not in matched_entry_names]
