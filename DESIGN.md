# Smart Script Browser — Cinema 4D 2026 Plugin (Research & Plan)

Status: planning, v2. No implementation yet. Target: Cinema 4D 2026 (2026.3 current, June 2026).

Legend: `ASSUME` = believed true, **must be verified on a real install before it is built on**.

---

## 0. Build-vs-reuse (decide this first)

C4D already ships two overlapping mechanisms. Naming them honestly before writing code:

| Existing | Covers | Gaps |
|---|---|---|
| **Script Manager** + Command Manager shortcuts | running scripts, per-script hotkeys | flat list, no tags, no search, no metadata |
| **Asset Browser** (+ Python Asset API: `CategoryAssetInterface`, `KeywordAssetInterface`, asset databases) | categories, keywords, favorites, smart folders, search, DB sync | scripts are not a native asset type (would need a custom third-party type); assets live in a database, not plain `.py` files in git; heavyweight UI; no frecency, no context-awareness |

**Three options:**
- **A. Custom index (recommended).** Own JSON index over plain `.py` files on disk. Files stay in git, metadata travels in the file, full control over ranking/UX.
- **B. Build on the Asset API.** Reuses Maxon's keyword/category/search infrastructure and DB sync across machines. Cost: scripts become assets (leaves the git-friendly folder model), custom asset type is significant work, and the Asset API surface is large.
- **C. Do nothing** — use Asset Browser keywords + Command Manager shortcuts.

Recommendation: **A**, because the git-tracked plain-file model and the ranking/context features in §4 are the actual value, and neither is reachable through B. But **spend one hour in the Asset Browser first** tagging a few scripts; if it turns out to be adequate, C is a legitimate outcome and saves weeks. This is the one decision worth testing before committing.

Also survey prior art before building: several community "user script manager" plugins already exist. If one is close, forking beats greenfield.

---

## 1. Research findings

### Grounded
- Current line: **C4D 2026.3**, Python SDK `2026.3.0`.
- Plugins are `.pyp` files in a plugins directory; they surface under the **Extensions** menu.
- UI = `c4d.gui.GeDialog`; custom drawing = `c4d.gui.GeUserArea`; trees = `TreeViewCustomGui` + `TreeViewFunctions`. A `CommandData` plugin owns and opens the dialog.
- User scripts folder (native Script Manager; bindable to shortcuts via Command Manager):
  - Win: `%APPDATA%\Maxon\<version>\library\scripts`
  - macOS: `~/Library/Preferences/Maxon/<version>/library/scripts`
- User plugins folder: sibling `library/plugins`.
- Asset Browser supports keywords, categories, favorites and saved smart searches, scriptable via the Asset API.

### To verify (blocking assumptions)
| # | `ASSUME` | How to verify | Blocks |
|---|---|---|---|
| V1 | Embedded interpreter is **Python 3.11** | `import sys; print(sys.version)` in Script Manager | core syntax level |
| V2 | **No PySide bundled** in C4D's interpreter | `import PySide6` in Script Manager | entire UI stack |
| V3 | Script Manager execs the file, then calls `main()` if defined | run a probe script that prints `__name__`, `__file__`, `globals().keys()` | §3 runner |
| V4 | `doc`, `op` are injected as globals; `c4d` pre-imported | same probe | §3 runner |
| V5 | Script Manager wraps execution in its own undo step | run a probe that creates an object, then press Ctrl+Z once | §3 undo semantics |
| V6 | No official "execute .py file" API exists | search SDK for a script-execution entry point | §3 |

V3–V5 are the highest-risk items in the project. **Write the probe script and run it before anything else.**

---

## 2. Scope

Dockable panel indexing the user's script collection: categories, tags, search, favourites/recents, run, metadata editing. Plus a **command palette** (§4) which is likely the highest daily value.

Non-goals (v1): cloud sync, in-panel code editing, marketplace, script authoring/scaffolding.

---

## 3. Runner specification (highest-risk component — design it, don't improvise)

Executing an arbitrary `.py` is the core of the product. Pin the semantics:

```
run(script_path):
  src = read fresh from disk        # never cache source; file may have changed
  ns  = {
    "__name__": "__main__",         # so `if __name__ == "__main__":` blocks fire  (V3)
    "__file__": script_path,        # scripts locate sibling resources through this
    "c4d": c4d,
    "doc": c4d.documents.GetActiveDocument(),
    "op":  doc.GetActiveObject(),
  }
  sys.path.insert(0, dirname(script_path))   # sibling imports; remove in finally
  try:
      exec(compile(src, script_path, "exec"), ns)
      if callable(ns.get("main")): ns["main"]()      # (V3)
  except Exception:
      capture traceback -> C4D console + panel status line; never let the dialog die
  finally:
      restore sys.path
      c4d.EventAdd()                # refresh viewport/managers
```

Open points to settle with the V3–V5 probe:
- **Undo.** If C4D does not auto-wrap our exec (unlike Script Manager), wrap in `doc.StartUndo()` / `doc.EndUndo()`. Wrapping when C4D already wraps produces nested/broken undo — verify before choosing. Getting this wrong means a user loses work.
- **Thread.** Run on the main thread (GeDialog commands already are). Never exec from a `C4DThread`.
- **Fresh exec every run**, never `import` — avoids stale-module confusion when the user edits a script and re-runs.

**Compatibility gate:** the existing 4 scripts must run unchanged through this runner. That is the acceptance test for Phase 2.

---

## 4. The "smart" layer

Categories + tags alone is a file browser. These are what make it worth building:

1. **Frecency ranking** — order by `frequency × recency` decay (Chrome URL-bar style). Single highest-value feature; the 5 scripts you use weekly surface without typing.
2. **Command palette mode** — one global hotkey opens a bare search field: type 3 chars, `Enter` runs, panel closes. Faster than any browser panel. Should ship in Phase 2, not last.
3. **Fuzzy / subsequence matching** — `fmn` matches `Fix_Mixamo_Names`. Substring matching is not enough.
4. **Auto-tagging via AST** — parse imports and attribute chains (`c4d.modules.mograph`, `BaseObject`, `Ttexture`, `CTrack`) into suggested tags. Zero authoring effort for the initial library, and the user only corrects.
5. **Context-awareness** — boost or grey out scripts based on scene state (polygon object selected, joints selected, nothing selected). Declared per script:
   `# @needs: polygon-selection` → panel shows it disabled with the reason when unmet.
6. **Destructive guard** — `# @destructive: true` triggers a confirm dialog. Batch operations on a real scene warrant it.
7. **Parameters (stretch)** — `# @param count:int=10` auto-generates a small GeDialog before running, so one parameterised script replaces five near-duplicates.

---

## 5. Indexing — safety and performance

**Safety rule (non-negotiable): indexing must never import or exec a script.** Read the text, parse with `ast.parse`, extract the header comment block. Scanning a folder must never be able to run code. This rules out the tempting "import the module and read `__tags__`" design.

**Performance budget:** cold scan of 1000 scripts < 2 s; warm panel open < 100 ms.
Cache key per file: `(path, mtime, size)`. Re-parse only on change. Rescan on panel focus + manual refresh button. If cold scan exceeds budget, move it to a `c4d.threading.C4DThread` and populate the list progressively — do not block the UI thread.

**Collisions:** key everything by absolute path; two scripts named `Cleanup.py` in different roots are distinct, disambiguated in the UI by parent folder.

---

## 6. Metadata

Source of truth = **inline header in each script**. It travels with the file, survives moves, diffs in git, and is shared for free when the repo is cloned — which is the main argument for option A in §0.

```python
# @title:      Fix Mixamo Names
# @category:   Rigging/Mixamo
# @tags:       mixamo, rename, cleanup
# @desc:       Strips the "mixamorig:" prefix from selected joints.
# @needs:      selection
# @destructive: true
# @icon:       fix_mixamo.png
# @version:    1.0
```

Grammar: contiguous `# @key: value` lines in the first N lines of the file. Unknown keys ignored (forward-compatible). Missing header → degrade gracefully: title from filename, category from folder path, no tags. **All 4 existing scripts currently have no header and must work.**

Runtime-only fields (`run_count`, `last_run`, `favorite`) live **only** in the index, keyed by path — never written back into source files. Sidecar `.meta.json` for scripts you cannot edit (vendored/third-party).

---

## 7. Architecture

```
plugin/
  script_browser.pyp          # CommandData registration + dialog wiring
  core/                       # zero c4d imports — unit-testable anywhere
    scanner.py                # walk roots, mtime cache, incremental reindex
    metadata.py               # header grammar parse + ast auto-tagging
    model.py                  # Script / Category / Tag / Library dataclasses
    store.py                  # index.json + settings.json, schema migration
    search.py                 # fuzzy match + tag/category filter + frecency rank
  ui/                         # c4d-bound
    panel.py                  # GeDialog: tree + list + search + actions
    palette.py                # command-palette dialog
    meta_editor.py            # header editor
  runner.py                   # §3
  res/                        # icons, strings
```

The `core/` ↔ `c4d` split is the main testability decision: everything with logic runs under plain pytest with no C4D present.

**Dockability:** open with `GeDialog.Open(c4d.DLG_TYPE_ASYNC, pluginid, ...)` and implement `CommandData.RestoreLayout()`, otherwise the docked panel vanishes on restart. Easy to forget, annoying to retrofit.

**Storage:** `index.json` + `settings.json` in the plugin's user-prefs folder. Both carry `"schema": 1` from day one, with a migration function — cheap now, painful later.

---

## 8. Plugin IDs (procurement blocker — start now)

- The plugin needs **unique IDs registered at developers.maxon.net**, tied to your Maxon account. Randomly chosen IDs collide with other plugins and corrupt user prefs. **This is on you, not me — I cannot obtain them.**
- Need: 1 ID for the CommandData, 1 for the palette, **plus a reserved block (~50–100) for hotkey slots.**
- **Per-script hotkeys** require one registered `CommandData` ID each, registered at plugin-load time. Design: reserve a fixed block of slot IDs; the user assigns *script → slot* in settings; the slot is then bindable in Command Manager like any command. Slot assignments persist in `settings.json`.

Request the IDs in week 1 — everything in Phase 4 blocks on them.

---

## 9. Testing (there is no CI in this repo today)

| Layer | Method | Runs where |
|---|---|---|
| `core/` | pytest, real fixtures from `scripts/` | anywhere, incl. CI |
| runner semantics | probe script (V3–V5) | manual, in C4D |
| `c4d`-touching code | `c4dpy` (Maxon's standalone interpreter; `ASSUME` needs a license) or a stubbed `c4d` module | dev machine |
| UI | manual smoke checklist, versioned in repo | in C4D |

Add a GitHub Action running pytest on `core/` — cheap, and it is the only part that can be tested automatically.

---

## 10. UX (keyboard-first, or it will not get used)

Search field focused on open · type-to-filter live · ↑/↓ navigate · `Enter` run · `Ctrl+Enter` open in editor · `Esc` clear then close · `Ctrl+F` favourite toggle. Sort modes: frecency (default) / name / recent / category. Tag chips are click-to-filter, shift-click to add (AND).

Errors surface in three places: C4D console (full traceback), panel status line (one line), and a rolling log file.

Cross-platform: `os.startfile` (Win) vs `open -R` (macOS) for reveal-in-finder; configurable external editor path.

---

## 11. Phases and acceptance criteria

| Phase | Deliverable | Done when |
|---|---|---|
| **0** | V1–V6 probe script | all six assumptions answered in writing, this doc updated |
| **1** | `core/` + tests | pytest green; indexes the 4 existing headerless scripts correctly; cold scan of 1000 synthetic scripts < 2 s |
| **2** | Panel + palette + runner | all 4 existing scripts run unchanged; undo behaves as a single step; panel docks and survives C4D restart |
| **3** | Tags, filters, favourites, frecency, metadata editor | tag a 30-script library and find any of them in < 3 keystrokes |
| **4** | Auto-tag, `@needs`, destructive guard, hotkey slots, thumbnails | hotkey bound to a script through Command Manager fires it |
| **5** (stretch) | `@param` auto-dialogs | one parameterised script replaces a family of near-duplicates |

---

## 12. Repo restructure (Phase 1, small but real)

- Move the 4 scripts into `scripts/<Category>/`, add headers to each.
- Fix the typo: `List_Hiearchy.py` → `List_Hierarchy.py`.
- Rename `OpenPose Sequence Generator From Selected Joints.py` — spaces in filenames are legal but awkward for path handling and shortcuts.
- Rewrite `README.md`: it currently documents only the hierarchy printer, not the repo.
- Keep `plugin/` and `scripts/` as separate trees so the plugin can be released independently of the script library.

---

## 13. Distribution

Ship as a folder (`ScriptBrowser/script_browser.pyp` + `res/`) zipped per release; install = drop into the plugins dir and restart C4D. Version in the plugin name string, changelog in repo. `ASSUME` 2024/2025 also work if all are Python 3.11 — cheap to support, but only claim it after testing on each.

---

## 14. Open questions

1. **§0 first**: does the Asset Browser already solve enough of this? (spend an hour before building)
2. Index roots: native scripts folder, this repo, or a configurable list? (recommend: configurable, seeded with both)
3. Category source: folders, `@category`, or both? (recommend: both, metadata wins)
4. Target 2026 only, or 2024/2025 too?
5. Is the command palette (§4.2) more valuable to you than the browser panel? If yes, reorder Phase 2 to ship it first.
