import io
import subprocess
import tarfile
import zipfile
from pathlib import Path

import pytest

from obs_plugin_manager import archive, remapper


def _make_tar_with_traversal(tar_path: Path) -> None:
    with tarfile.open(tar_path, "w:gz") as tf:
        data = b"evil payload"
        info = tarfile.TarInfo(name="../../evil.txt")
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))


def _make_zip_with_traversal(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "evil payload")


def test_safe_extract_tar_rejects_path_traversal(tmp_path):
    tar_path = tmp_path / "evil.tar.gz"
    _make_tar_with_traversal(tar_path)
    dest = tmp_path / "dest"
    dest.mkdir()

    with pytest.raises(archive.ArchiveSecurityError):
        archive._safe_extract_tar(tar_path, dest)


def test_safe_extract_zip_rejects_path_traversal(tmp_path):
    zip_path = tmp_path / "evil.zip"
    _make_zip_with_traversal(zip_path)
    dest = tmp_path / "dest"
    dest.mkdir()

    with pytest.raises(archive.ArchiveSecurityError):
        archive._safe_extract_zip(zip_path, dest)


def test_extract_to_scratch_handles_plain_zip(tmp_path):
    zip_path = tmp_path / "plugin.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("bin/64bit/myplugin.so", "fake binary")
        zf.writestr("data/locale/en-US.ini", "Name=My Plugin")

    scratch_root = tmp_path / "scratch"
    extracted = archive.extract_to_scratch(zip_path, scratch_root)

    assert (extracted / "bin" / "64bit" / "myplugin.so").exists()
    assert (extracted / "data" / "locale" / "en-US.ini").exists()


def test_unsupported_archive_raises(tmp_path):
    junk_path = tmp_path / "not-an-archive.bin"
    junk_path.write_bytes(b"not a real archive")

    with pytest.raises(archive.UnsupportedArchiveError):
        archive.extract_to_scratch(junk_path, tmp_path / "scratch")


def _ar_available() -> bool:
    try:
        subprocess.run(["ar", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


@pytest.mark.skipif(not _ar_available(), reason="binutils 'ar' not available")
def test_deb_extraction_and_remap_pulls_so_and_data(tmp_path):
    # Build a minimal real .deb: ar archive containing data.tar.xz with a
    # standard OBS-plugin-template Debian layout.
    build_dir = tmp_path / "build"
    data_tree = build_dir / "data_tree"
    plugin_dir = data_tree / "usr" / "lib" / "x86_64-linux-gnu" / "obs-plugins"
    share_dir = data_tree / "usr" / "share" / "obs" / "obs-plugins" / "myplugin" / "locale"
    plugin_dir.mkdir(parents=True)
    share_dir.mkdir(parents=True)
    (plugin_dir / "myplugin.so").write_bytes(b"fake binary")
    (share_dir / "en-US.ini").write_text("Name=My Plugin")

    data_tar_path = build_dir / "data.tar.xz"
    with tarfile.open(data_tar_path, "w:xz") as tf:
        tf.add(data_tree, arcname=".")

    deb_path = build_dir / "myplugin.deb"
    (build_dir / "debian-binary").write_text("2.0\n")
    subprocess.run(
        ["ar", "rc", str(deb_path), "debian-binary", "data.tar.xz"],
        cwd=build_dir,
        check=True,
    )

    scratch_root = tmp_path / "scratch"
    extracted = archive.extract_to_scratch(deb_path, scratch_root)

    shape = remapper.classify_tree(extracted)
    assert shape == remapper.TreeShape.DEB_DATA_TREE

    dest = tmp_path / "built_plugin"
    remapper.remap_to_plugin_layout(extracted, shape, dest)
    remapper.validate_plugin_layout(dest)

    assert (dest / "bin" / "64bit" / "myplugin.so").exists()
    assert (dest / "data" / "locale" / "en-US.ini").exists()


@pytest.mark.skipif(not _ar_available(), reason="binutils 'ar' not available")
def test_deb_extraction_handles_obs_modules_plugins_convention(tmp_path):
    # Real-world shape confirmed against an actual downloaded .deb
    # (obs-advanced-masks 1.6.1): usr/lib/x86_64-linux-gnu/obs-modules/plugins/
    # + usr/share/obs/obs-modules/plugins/<name>/, NOT the older
    # usr/share/obs/obs-plugins/<name>/ convention.
    build_dir = tmp_path / "build"
    data_tree = build_dir / "data_tree"
    plugin_dir = data_tree / "usr" / "lib" / "x86_64-linux-gnu" / "obs-modules" / "plugins"
    share_dir = (
        data_tree / "usr" / "share" / "obs" / "obs-modules" / "plugins" / "myplugin" / "shaders"
    )
    plugin_dir.mkdir(parents=True)
    share_dir.mkdir(parents=True)
    (plugin_dir / "myplugin.so").write_bytes(b"fake binary")
    (share_dir / "mask.effect").write_text("effect source")

    data_tar_path = build_dir / "data.tar.xz"
    with tarfile.open(data_tar_path, "w:xz") as tf:
        tf.add(data_tree, arcname=".")

    deb_path = build_dir / "myplugin.deb"
    (build_dir / "debian-binary").write_text("2.0\n")
    subprocess.run(
        ["ar", "rc", str(deb_path), "debian-binary", "data.tar.xz"],
        cwd=build_dir,
        check=True,
    )

    extracted = archive.extract_to_scratch(deb_path, tmp_path / "scratch")
    shape = remapper.classify_tree(extracted)
    dest = tmp_path / "built_plugin"
    remapper.remap_to_plugin_layout(extracted, shape, dest)
    remapper.validate_plugin_layout(dest)

    assert (dest / "bin" / "64bit" / "myplugin.so").exists()
    assert (dest / "data" / "shaders" / "mask.effect").exists()
