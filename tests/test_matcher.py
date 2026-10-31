import json
from pathlib import Path

from obs_plugin_manager.matcher import match, slugify
from obs_plugin_manager.models import CatalogEntry, InstalledPlugin

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_catalog.json"


def _load_catalog():
    raw = json.loads(FIXTURE_PATH.read_text())
    return [CatalogEntry.from_api(entry) for entry in raw["plugins"]]


def _installed(folder_name: str, so_basename: str) -> InstalledPlugin:
    return InstalledPlugin(
        folder_name=folder_name,
        folder_path=Path(f"/fake/{folder_name}"),
        so_path=Path(f"/fake/{folder_name}/bin/64bit/{so_basename}.so"),
        so_basename=so_basename,
    )


def test_case_mismatched_folder_and_so_name_matches_by_module_name():
    # Reproduces the real installed layout: folder "Tuna", .so "tuna.so".
    catalog = _load_catalog()
    installed = [_installed("Tuna", "tuna")]

    results = match(installed, catalog)

    assert len(results) == 1
    assert results[0].catalog_entry is not None
    assert results[0].catalog_entry.name == "Tuna"


def test_exact_module_name_match():
    catalog = _load_catalog()
    installed = [_installed("obs-advanced-masks", "obs-advanced-masks")]

    results = match(installed, catalog)

    assert results[0].catalog_entry.module_name == "obs-advanced-masks"


def test_unrecognized_plugin_stays_unmatched():
    catalog = _load_catalog()
    installed = [_installed("my-personal-plugin", "my-personal-plugin")]

    results = match(installed, catalog)

    assert results[0].catalog_entry is None


def test_slugify_strips_common_suffixes():
    assert slugify("VinciFlow Lower Thirds for OBS Studio") == "vinciflow-lower-thirds"
    assert slugify("Advanced Masks") == "advanced-masks"
