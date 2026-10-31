"""Builds the merged table rows: installed+matched, installed+unmanaged, and
not-yet-installed catalog entries, all in one pure/testable function.
"""

from . import version_compare
from .log_scanner import extract_version_for
from .models import PluginRow


def build_rows(match_results: list, catalog: list, log_text: str) -> list:
    rows = []
    matched_catalog_ids = set()

    for result in match_results:
        installed = result.installed
        entry = result.catalog_entry

        if entry is None:
            rows.append(
                PluginRow(
                    display_name=installed.folder_name,
                    installed_version="unknown",
                    latest_version="",
                    status="installed_unmanaged",
                    catalog_entry=None,
                    installed=installed,
                    forum_url="",
                )
            )
            continue

        matched_catalog_ids.add(id(entry))
        installed_version = "unknown"
        if entry.search_string:
            detected = extract_version_for(entry.search_string, log_text)
            if detected:
                installed_version = detected

        status = version_compare.compare(installed_version, entry.version)
        rows.append(
            PluginRow(
                display_name=entry.name,
                installed_version=installed_version,
                latest_version=entry.version,
                status=status,
                catalog_entry=entry,
                installed=installed,
                forum_url=entry.url,
            )
        )

    for entry in catalog:
        if id(entry) in matched_catalog_ids:
            continue
        has_linux = bool(entry.linux_download_url)
        rows.append(
            PluginRow(
                display_name=entry.name,
                installed_version="",
                latest_version=entry.version,
                status="not_installed" if has_linux else "not_available_linux",
                catalog_entry=entry,
                installed=None,
                forum_url=entry.url,
            )
        )

    rows.sort(key=lambda r: r.display_name.lower())
    return rows
