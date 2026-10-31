"""Classifies an extracted plugin archive's directory shape and remaps it
into the OBS user-plugin layout: <dest>/bin/64bit/<name>.so + <dest>/data/...

Two shapes are handled generically (no per-plugin hardcoding):
  - ALREADY_STRUCTURED: the archive already is a bin/64bit + data tree.
  - DEB_DATA_TREE: a typical Debian package data tree, where the .so lives
    under usr/lib*/obs-plugins/ and its assets (if any) live under a
    same-named directory beneath usr/share/obs/obs-plugins/.
"""

import shutil
from enum import Enum, auto
from pathlib import Path
from typing import Optional


class TreeShape(Enum):
    ALREADY_STRUCTURED = auto()
    DEB_DATA_TREE = auto()
    UNKNOWN = auto()


class RemapError(Exception):
    pass


def classify_tree(root: Path) -> TreeShape:
    bin64 = root / "bin" / "64bit"
    if bin64.is_dir() and any(bin64.glob("*.so")):
        return TreeShape.ALREADY_STRUCTURED
    if list(root.rglob("*.so")):
        return TreeShape.DEB_DATA_TREE
    return TreeShape.UNKNOWN


def _single_top_level_child(root: Path) -> Optional[Path]:
    """If `root` contains exactly one subdirectory and no files, returns it
    (archives sometimes wrap everything in one extra top-level folder)."""
    children = list(root.iterdir())
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return None


def remap_already_structured(root: Path, dest_plugin_dir: Path) -> None:
    source = root
    bin64 = source / "bin" / "64bit"
    if not (bin64.is_dir() and any(bin64.glob("*.so"))):
        inner = _single_top_level_child(root)
        if inner is not None and (inner / "bin" / "64bit").is_dir():
            source = inner
        else:
            raise RemapError(f"expected bin/64bit/*.so under {root}, not found")

    dest_plugin_dir.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        shutil.move(str(item), dest_plugin_dir / item.name)


def remap_deb_tree(root: Path, dest_plugin_dir: Path) -> None:
    so_files = list(root.rglob("*.so"))
    if len(so_files) != 1:
        raise RemapError(f"expected exactly one .so under {root}, found {len(so_files)}: {so_files}")
    so_path = so_files[0]
    module_name = so_path.stem

    bin64_dest = dest_plugin_dir / "bin" / "64bit"
    bin64_dest.mkdir(parents=True, exist_ok=True)
    shutil.move(str(so_path), bin64_dest / so_path.name)

    # The data/assets dir is always named exactly after the module, but its
    # parent path varies by packaging convention (observed in the wild:
    # usr/share/obs/obs-plugins/<name>/ on older templates, and
    # usr/share/obs/obs-modules/plugins/<name>/ on current ones) - so match
    # by directory name alone rather than hardcoding either parent path.
    share_candidates = [
        d
        for d in root.rglob("*")
        if d.is_dir() and d.name.lower() == module_name.lower() and d != so_path.parent
    ]
    if share_candidates:
        share_dir = share_candidates[0]
        data_dest = dest_plugin_dir / "data"
        data_dest.mkdir(parents=True, exist_ok=True)
        for item in share_dir.iterdir():
            shutil.move(str(item), data_dest / item.name)


def remap_to_plugin_layout(root: Path, shape: TreeShape, dest_plugin_dir: Path) -> None:
    if shape is TreeShape.ALREADY_STRUCTURED:
        remap_already_structured(root, dest_plugin_dir)
    elif shape is TreeShape.DEB_DATA_TREE:
        remap_deb_tree(root, dest_plugin_dir)
    else:
        raise RemapError(f"could not classify extracted tree at {root}")


def validate_plugin_layout(dest_plugin_dir: Path) -> None:
    bin64 = dest_plugin_dir / "bin" / "64bit"
    so_files = list(bin64.glob("*.so")) if bin64.is_dir() else []
    if len(so_files) != 1:
        raise RemapError(
            f"expected exactly one .so under {bin64}, found {len(so_files)}"
        )
