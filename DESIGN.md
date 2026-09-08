# Smart Script Browser — Cinema 4D 2026 Plugin (Research & Plan)

Status: planning. No code yet. Target: Cinema 4D 2026 (2026.3 current, June 2026).

## 1. Research findings

### Runtime / SDK (grounded)
- Current release line: **C4D 2026.3**, Python SDK `2026.3.0`. Docs: developers.maxon.net/docs/py.
- Plugins are `.pyp` files placed in a plugins directory; they appear under the **Extensions** menu.
- GUI is built with `c4d.gui.GeDialog`; custom-drawn widgets use `c4d.gui.GeUserArea`. A `CommandData` plugin owns and opens the dialog instance.
- User scripts folder (native Script Manager reads these; can be bound to shortcuts via Command Manager):
  - Win: `%APPDATA%\Maxon\<version>\library\scripts`
  - macOS: `~/Library/Preferences/Maxon/<version>/library/scripts`
- User plugins folder: sibling `library/plugins` (or any path in the plugin search list).

### Assumptions to verify against a real 2026 install
- `ASSUME` embedded interpreter is **Python 3.11** (unchanged since 2023.2 line). Verify with `sys.version` in Script Manager.
- `ASSUME` **PySide is NOT bundled** in C4D's embedded interpreter. Consequence: the UI **must** use `c4d.gui` (GeDialog / GeUserArea / TreeViewCustomGui), not PySide6. This overrides the default-PySide6 preference for anything running *inside* C4D. (A separate PySide6 companion app for metadata authoring outside C4D is possible later — see §6.)
- `ASSUME` no official "run this .py file" API. Scripts are executed the way Script Manager does: read source, `exec(compile(src, path, "exec"), namespace)` with `doc`/`op` injected.

## 2. Product scope

A dockable panel that indexes the user's script collection and makes it fast to find and run, with:
- **Categories** — folder-tree derived + optional virtual categories from metadata.
- **Tagging** — many-to-many tags per script, filterable (chip filters, AND/OR).
- **Search** — live text search over name, description, tags.
- **Favorites / Recents / usage count.**
- **Actions** — Run, Open in editor, Reveal in file browser, Edit metadata.
- Optional: thumbnails, code preview, per-script hotkey binding.

Non-goals (v1): cloud sync, script editing inside the panel, marketplace.

## 3. Architecture

```
CommandData plugin (RegisterCommandPlugin)
  └─ GeDialog (async, dockable via RestoreLayout)
       ├─ Toolbar: search field, tag filter, rescan, settings
       ├─ Left: category/tag TreeView (TreeViewCustomGui + TreeViewFunctions)
       ├─ Right: script list (TreeView or GeUserArea rows) + description
       └─ Footer: Run / Edit meta / Reveal / Open
Core (pure-Python, C4D-independent, unit-testable):
  ├─ scanner  — walk roots, detect .py, mtime-based incremental reindex
  ├─ metadata — parse inline header block + merge sidecar overrides
  ├─ model    — Script, Category, Tag, Library dataclasses
  ├─ store    — library.json cache (load/save), settings.json
  └─ search   — filter/rank by text + tags + category
Runner (C4D-dependent): exec script with injected globals.
```

Split C4D-free core from the C4D-bound UI/runner so the core is testable off-app.

## 4. Metadata model

Source of truth = **inline header in each script** (non-invasive, travels with the file), cached into `library.json`. Optional sidecar for scripts you can't edit.

Inline header (parsed from the leading comment/docstring block):
```python
# @title: Fix Mixamo Names
# @category: Rigging/Mixamo
# @tags: mixamo, rename, cleanup
# @desc: Strips the "mixamorig:" prefix from selected joints.
# @icon: fix_mixamo.png
```
`Script` fields: `path, title, category, tags[], desc, icon, mtime, run_count, last_run, favorite`.
Runtime-only fields (`run_count`, `last_run`, `favorite`) live in `library.json`, keyed by path — never written back into source files.

Categories: `A/B/C` path string → nested tree; falls back to on-disk folder path when `@category` absent.

## 5. Storage locations
- `library.json`, `settings.json` in the plugin's user-prefs folder (`storage.GeGetC4DPath` / plugin path). Configurable list of **root folders** to index (default: the native user scripts folder + this repo).
- Thumbnails: sidecar `<name>.png` next to the script or in `@icon`.

## 6. Metadata authoring
- v1: edit inline headers by hand + an in-panel "Edit metadata" dialog that rewrites the header block.
- Optional later: standalone **PySide6** desktop app (runs in normal Python, not C4D) to bulk-tag/organize the library.json — this is where the PySide6 preference fits.

## 7. Delivery phases
1. **Core (off-app, tested):** scanner + metadata parser + model + store + search. pytest on the 4 existing scripts. No C4D needed.
2. **Read-only panel:** GeDialog + category tree + list + search + **Run**. Validate in C4D 2026.
3. **Tagging + filters + favorites/recents + metadata editor.**
4. **Polish:** thumbnails, code preview, per-script hotkey (dynamic CommandData registration), incremental rescan on focus.

## 8. Key risks / decisions
- **Execution model:** confirm `doc`/`op`/`c4d` injection matches Script Manager so existing scripts run unchanged. Highest-risk item; prototype first in phase 2.
- **TreeView vs GeUserArea:** native `TreeViewCustomGui` is less work and gives sorting/columns; custom chip/thumbnail UI needs `GeUserArea`. Recommend TreeView for v1, GeUserArea only for thumbnails.
- **Repo layout:** move the 4 loose scripts into a `scripts/` tree with categories, keep plugin in `plugin/`.
- **Existing scripts** have no headers — scanner must degrade gracefully (title from filename, no tags).

## 9. Open questions for you
1. Index only the native user scripts folder, this repo, or a user-configurable list? (recommend: configurable list, seeded with both)
2. Category source: folders, metadata `@category`, or both? (recommend: both, metadata wins)
3. Thumbnails in v1 or defer? (recommend: defer to phase 4)
4. Confirm target = 2026.x only, or also support 2024/2025 (Python 3.11 across all → likely free)?
