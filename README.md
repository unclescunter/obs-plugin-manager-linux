# OBS Plugin Manager (Linux)

A desktop GUI for managing [OBS Studio](https://obsproject.com/) plugins on Linux — the
"Pluginstaller" Windows users already have, built for the rest of us.

On Linux, installing or updating an OBS plugin today means finding it on the
[forum](https://obsproject.com/forum/plugins/), downloading the right archive, figuring out
whether it's a `.zip`, `.tar.xz`, or `.deb`, extracting it, and copying the right files into
`~/.config/obs-studio/plugins/<name>/bin/64bit/` and `data/` by hand. There's no way to see what
you have installed, what version it is, or whether something newer exists. This tool fixes that:
it lists available plugins, shows what's installed and whether it's current, and installs or
updates with one click — handling the archive format and folder layout for you.

## How it works

**Catalog.** There's no Linux-native plugin registry, and obsproject.com's forum has no public
API — but the existing Windows tool, [StreamUP's
Pluginstaller](https://github.com/StreamUPTips/Pluginstaller-V2), turned out to pull its list from
a plain, unauthenticated, CORS-open JSON endpoint: `https://api.streamup.tips/plugins`. It already
has per-OS download URLs (125 of ~166 entries have a Linux `.deb`, almost always a GitHub Release
asset), so this tool uses the same endpoint, with a local on-disk mirror kept on every successful
fetch so it keeps working if that API is ever briefly unreachable.

**Version detection.** OBS itself doesn't track plugin versions anywhere usable — its own
`plugin_manager/modules.json` has every version field blank. The one place a real version number
shows up is OBS's own log file, where some plugins print a line like `[name] plugin loaded ...
(version X.Y.Z)` on startup. The catalog above ships a `searchString` for exactly this purpose
(the same mechanism StreamUP's own GPL-licensed `obs-streamup` plugin uses) — this tool greps the
newest OBS log for it and extracts the version that follows. No match means no guess: the plugin is
shown as "unknown" rather than assumed up to date or out of date.

**Install / update.** Downloads are `.deb` (an `ar` archive containing a `data.tar.*`), `.zip`, or
`.tar.*`, with the actual `.so` and data buried at different paths depending on which packaging
convention the plugin's CI happens to use (this tool found and worked around a real-world
inconsistency here — see [Notes](#notes) below). Everything is extracted into an isolated scratch
directory first, validated against path traversal, and only copied into the real
`~/.config/obs-studio/plugins/<name>/` once a valid `bin/64bit/<name>.so` + `data/` layout has been
confirmed. Updating an existing plugin always moves the old folder aside into a timestamped backup
first — never deletes it — and automatically restores that backup if anything goes wrong
mid-install.

**Plugins not in the catalog** (something you installed manually from elsewhere, or a
distro-patched fork) are still listed, so you can see everything in one place, but they're left
alone — install/update actions simply aren't offered for them.

## Usage

```bash
git clone https://github.com/unclescunter/obs-plugin-manager-linux.git
cd obs-plugin-manager-linux
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Close OBS Studio before installing or updating a plugin that's currently loaded.

## Project layout

```
obs_plugin_manager/
  catalog.py        # fetch + local mirror of the plugin catalog
  log_scanner.py     # OBS-log-based version detection
  fs_scanner.py       # enumerates ~/.config/obs-studio/plugins/
  matcher.py           # matches installed folders to catalog entries
  archive.py            # safe download + extraction (.deb/.zip/.tar.*)
  remapper.py            # classifies + remaps extracted trees into bin/64bit + data/
  installer.py            # orchestrates download -> extract -> remap -> backup -> place
  state_store.py           # tracks what this tool has installed, for clean updates
  ui/                       # PySide6 main window, table model, dialogs
tests/                      # pytest suite, offline + a real .deb build/extract round-trip
```

## Notes

- Built against 11 real, working plugins as reference fixtures, and tested end-to-end against a
  real GitHub-hosted `.deb` release before touching a live install.
- While verifying this, a real packaging inconsistency turned up: some plugin `.deb`s ship their
  data under `usr/share/obs/obs-plugins/<name>/`, others under the newer
  `usr/share/obs/obs-modules/plugins/<name>/` — the remapper matches by directory name rather than
  hardcoding either parent path, so it isn't tied to either convention.
- The catalog source (`api.streamup.tips`) is a third party's API with no published terms for this
  kind of use; it's publicly reachable and already used by StreamUP's own public tools, but if it
  ever disappears, only `obs_plugin_manager/catalog.py`'s base URL needs to change to point at a
  replacement.

## Credits

- Plugin catalog data: [StreamUP](https://streamup.tips/) (`api.streamup.tips`), the same source
  used by their Windows [Pluginstaller](https://github.com/StreamUPTips/Pluginstaller-V2) and their
  GPL-2.0 [obs-streamup](https://github.com/StreamUPTips/obs-streamup) plugin.
- Plugin authors whose actual builds this tool installs — see each plugin's entry in the app for
  its forum/GitHub link.

## License

MIT — see [LICENSE](LICENSE).
