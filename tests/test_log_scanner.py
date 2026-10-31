from pathlib import Path

from obs_plugin_manager.log_scanner import extract_version_for

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_log_lines.txt"


def _log_text() -> str:
    return FIXTURE_PATH.read_text()


def test_simple_parenthesized_version():
    assert extract_version_for(
        "[distroav] plugin loaded (full NDI features) (version", _log_text()
    ) == "6.2.1"


def test_plugin_loaded_successfully_version():
    assert extract_version_for(
        "[obs-backgroundremoval] Plugin loaded successfully (version", _log_text()
    ) == "1.3.7"


def test_bare_release_number_non_semver():
    assert extract_version_for("[droidcam-obs] module loaded release", _log_text()) == "250"


def test_colon_version_with_trailing_rpc_version_takes_first_number():
    assert extract_version_for(
        "[obs-websocket] [obs_module_load] you can haz websockets (Version:", _log_text()
    ) == "5.7.4"


def test_version_without_parens():
    assert extract_version_for("[obs-browser]: Version", _log_text()) == "2.26.9"


def test_loaded_version_phrase():
    assert extract_version_for("[Advanced Masks] loaded version", _log_text()) == "1.1.0"


def test_missing_search_string_returns_none():
    assert extract_version_for("[nonexistent-plugin] loaded version", _log_text()) is None


def test_empty_search_string_returns_none():
    assert extract_version_for("", _log_text()) is None
    assert extract_version_for(None, _log_text()) is None
