"""Tolerant version comparison: proper semver via `packaging` where possible,
falling back to comparing tuples of extracted digits for non-semver strings
like "release 250".
"""

import re
from typing import Literal, Optional

from packaging.version import InvalidVersion, Version

Comparison = Literal["up_to_date", "update_available", "unknown"]

_DIGIT_RE = re.compile(r"\d+")


def _loose_key(value: str) -> tuple:
    digits = [int(x) for x in _DIGIT_RE.findall(value)]
    return tuple(digits) if digits else (0,)


def compare(installed: Optional[str], latest: Optional[str]) -> Comparison:
    if not installed or installed == "unknown" or not latest:
        return "unknown"
    if installed == latest:
        return "up_to_date"
    try:
        return "up_to_date" if Version(installed) >= Version(latest) else "update_available"
    except InvalidVersion:
        return "up_to_date" if _loose_key(installed) >= _loose_key(latest) else "update_available"
