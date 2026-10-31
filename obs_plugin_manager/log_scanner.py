"""Detects installed plugin versions by scraping OBS's own log file for the
catalog's `searchString`, the same mechanism StreamUP's tools use. This is a
real signal (the plugin itself printed it on load), not a guess.
"""

import re
from pathlib import Path
from typing import Optional

from . import paths

VERSION_NUM_RE = re.compile(r"(\d+(?:\.\d+){0,3})")


def find_latest_log(logs_dir: Optional[Path] = None) -> Optional[Path]:
    logs_dir = logs_dir if logs_dir is not None else paths.obs_logs_dir()
    if not logs_dir.is_dir():
        return None
    log_files = sorted(logs_dir.glob("*.txt"))
    return log_files[-1] if log_files else None


def extract_version_for(search_string: str, log_text: str) -> Optional[str]:
    if not search_string:
        return None
    idx = log_text.find(search_string)
    if idx == -1:
        idx = log_text.lower().find(search_string.lower())
        if idx == -1:
            return None
    line_end = log_text.find("\n", idx)
    window = log_text[idx + len(search_string): line_end if line_end != -1 else None]
    match = VERSION_NUM_RE.search(window)
    return match.group(1) if match else None


def load_log_text(log_path: Optional[Path]) -> str:
    if log_path is None or not log_path.exists():
        return ""
    try:
        return log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
