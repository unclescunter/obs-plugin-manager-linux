"""Exercises the backup-then-replace-then-rollback-on-failure branch of
_place_into_real_plugins_dir directly. The 404-download forced-failure
scenario (tested manually in the scratch dry run) fails before any backup
happens; this test targets the other failure point, after the existing
folder has already been moved aside.
"""

import pytest

from obs_plugin_manager import installer, paths


@pytest.fixture(autouse=True)
def scratch_dirs(tmp_path, monkeypatch):
    plugins_dir = tmp_path / "plugins"
    backups_dir = tmp_path / "backups"
    plugins_dir.mkdir()
    backups_dir.mkdir()
    monkeypatch.setattr(paths, "obs_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(paths, "backup_dir", lambda: backups_dir)
    return plugins_dir, backups_dir


def test_successful_place_moves_new_content_into_real_dest(scratch_dirs, tmp_path):
    plugins_dir, _ = scratch_dirs
    built = tmp_path / "built"
    built.mkdir()
    (built / "marker.txt").write_text("new content")

    backup_path = installer._place_into_real_plugins_dir(built, "my-plugin")

    assert backup_path is None  # nothing existed before, so no backup
    assert (plugins_dir / "my-plugin" / "marker.txt").read_text() == "new content"


def test_update_backs_up_existing_folder_before_replacing(scratch_dirs, tmp_path):
    plugins_dir, backups_dir = scratch_dirs
    existing = plugins_dir / "my-plugin"
    existing.mkdir()
    (existing / "marker.txt").write_text("old content")

    built = tmp_path / "built"
    built.mkdir()
    (built / "marker.txt").write_text("new content")

    backup_path = installer._place_into_real_plugins_dir(built, "my-plugin")

    assert backup_path is not None
    assert (backup_path / "marker.txt").read_text() == "old content"
    assert (plugins_dir / "my-plugin" / "marker.txt").read_text() == "new content"


def test_failed_move_into_place_restores_the_backup(scratch_dirs, tmp_path):
    plugins_dir, backups_dir = scratch_dirs
    existing = plugins_dir / "my-plugin"
    existing.mkdir()
    (existing / "marker.txt").write_text("original content")

    # A built_plugin_dir that doesn't exist makes the final shutil.move fail
    # *after* the existing folder has already been backed up - exactly the
    # failure window the automatic rollback exists to cover.
    nonexistent_built = tmp_path / "does_not_exist"

    with pytest.raises(FileNotFoundError):
        installer._place_into_real_plugins_dir(nonexistent_built, "my-plugin")

    # Rolled back: the original folder is back in place, under its original name.
    assert (plugins_dir / "my-plugin" / "marker.txt").read_text() == "original content"
    # And no orphaned backup was left behind.
    assert list(backups_dir.iterdir()) == []
