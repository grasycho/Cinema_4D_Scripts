# Smart Script Browser

Search, tag, favourite and run the scripts Cinema 4D already knows about.

Built on C4D's own script registry (`GetScriptHead()`), not on a separate
index: the plugin never scans folders and never has a stale cache. What it adds
is the four things C4D has no answer for — fuzzy search, tags, descriptions and
duplicate detection. See `../DESIGN.md` for why.

Target: **Cinema 4D 2026.3.0.4**, Windows, bundled Python 3.11.4.

## Install

1. Copy this whole folder, named `script_browser`, into the `plugins` folder of
   your C4D preferences directory:

   ```
   %APPDATA%\Maxon\Maxon Cinema 4D 2026_<hash>\plugins\script_browser\
   ```

   The preferences folder name carries an installation hash — `1ABCDC12` on the
   machine this was built against. **Never type it from a version string**: open
   the real path with *Edit → Preferences → Open Preferences Folder*. Create the
   `plugins` subfolder if it is not there.

   Installing under `C:\Program Files\Maxon Cinema 4D 2026\plugins` also works
   but Maxon advises against it: it needs administrator rights and an upgrade
   wipes it. To share one copy across several C4D versions, put the folder
   anywhere you like and add it under *Preferences → Plugins → Add Folder*.
2. Restart Cinema 4D. `script_browser.pyp` puts its own directory on
   `sys.path`, so `core/` and `ui/` resolve wherever the folder lives.
3. Two new commands appear in the Command Manager:
   - **Script Browser** — the dockable panel.
   - **Run Script** — the command palette. Bind it to a hotkey; it is the one
     you will use daily.

Before distributing the plugin, replace `PLUGIN_ID_PANEL` and
`PLUGIN_ID_PALETTE` in `script_browser.pyp` with ids registered at
<https://developers.maxon.net/>. The current values are development ids.

## Using it

**Palette** — hotkey, type a few characters, `Enter` runs the top hit. `fmn`
finds `Fix_Mixamo_Names`.

**Panel** — the same search plus:

| Scope | Shows |
|---|---|
| All | every saved script, alphabetically |
| Favourites | the ones you starred (`*` / `-` button on each row) |
| Recent | the last 10 you ran, newest first |
| Duplicates | same-stem scripts, e.g. `Mixamo_Helper` and `Mixamo_Helper_06` |

Click a name to run it. Click `i` to open the detail editor: tags (comma
separated), a one-line note, and buttons for **Open in editor**
(Script Manager), **Reveal** (Explorer) and **Save**.

Search matches name, folder, tags and description.

## Descriptions and icons

Same convention as the author's After Effects launcher: a `.txt` beside the
script with the same basename is its description, and an image with the same
basename is its icon. A description typed into the panel takes precedence over
the sidecar.

## Where metadata lives

One `library.json` under the resolved user library path, keyed by absolute
script path, carrying `"schema": 1`. Writes are atomic. Nothing is stored in
the scripts themselves — every `PYTHONSCRIPT_*` metadata field in C4D reads
empty, which is precisely why this plugin exists.

## Layout

```
script_browser.pyp   CommandData registration for both commands
registry.py          C4D's script tree: walk, filter, run, reveal
ui/state.py          the controller both dialogs drive
ui/panel.py          the dockable panel
ui/palette.py        the command palette
core/                zero c4d imports, pure pytest
  search.py          fuzzy match + ranking
  tags.py            library.json load/save/migrate
  dupes.py           same-stem detection
  sidecars.py        same-basename icon and .txt lookup
tests/               87 tests; c4d_stub.py fakes the registry tree
```

## Tests

```
cd plugin && python -m pytest -q
```

Runs anywhere — `core/` imports no `c4d`, and `registry.py` / `ui/state.py`
are tested against `tests/c4d_stub.py`, a fake built to the shape probe 3
measured. CI runs the same suite on Python 3.11, the version C4D bundles.

The stub proves the logic, not the application. The dialogs themselves are
untested code until someone runs `SMOKE.md` inside C4D.
