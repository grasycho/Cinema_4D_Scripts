# Smart Script Browser — Cinema 4D 2026 Plugin (Research & Plan)

Status: planning, v3. Phase 0 probe 1 has been run against a real install.
Target confirmed: **Cinema 4D 2026.3.0.4** (`GetC4DVersion() = 2026304`), Windows.

Legend: `MEASURED` = confirmed by `tools/phase0_probe.py` on the target machine.
`ASSUME` = still unverified. `OPEN` = probe run but answer not yet reported.

---

## 0. Build-vs-reuse (decide this first)

C4D ships two overlapping mechanisms:

| Existing | Covers | Gaps |
|---|---|---|
| **Script Manager** + Command Manager shortcuts | running scripts, per-script hotkeys | flat list, no tags, no search, no metadata |
| **Asset Browser** (+ Asset API — `maxon.AssetInterface`, `KeywordAssetInterface`, `CategoryAssetInterface`, `AssetDataBasesInterface`, all `MEASURED` present) | categories, keywords, favorites, smart folders, search, DB sync | scripts are not a native asset type; assets live in a database rather than plain `.py` files in git; heavyweight UI; no frecency, no context-awareness |

**Options:** **A.** Own JSON index over plain `.py` files (recommended). **B.** Build on the Asset API — now confirmed technically viable, all five interfaces exist. **C.** Do nothing; use Asset Browser keywords + Command Manager shortcuts.

Recommendation stands: **A**, for the git-tracked plain-file model and the ranking in §4. But §0 is still worth an hour of hands-on Asset Browser use before committing — C remains a legitimate outcome.

---

## 1. Environment (probe 1 results)

| # | Assumption | Result |
|---|---|---|
| V1 | Python 3.11 | **MEASURED — correct.** `3.11.4 (MSC v.1929 64-bit)`, host `Cinema 4D.exe` |
| V2 | No Qt bundled | **MEASURED — correct.** PySide6, PySide2, PyQt6, PyQt5, shiboken6, tkinter all absent. UI must be `c4d.gui`. Confirms PySide6 is only viable for an out-of-app companion tool (§6). |
| V3 | Script Manager calls `main()` | **MEASURED — WRONG. It does not.** See §3. |
| V4 | `doc`, `op`, `c4d` injected | **MEASURED — partly wrong.** Injected globals are exactly `['__builtins__', '__file__', '__name__', 'doc', 'op']`. `c4d` is **not** injected; scripts import it themselves. `__name__ == '__main__'`. `__file__ == 'scriptmanager'` — a literal string, not a path. |
| V5 | C4D auto-wraps script execution in undo | **OPEN** — probe inserted the two nulls; the manual Ctrl+Z result has not been reported yet. Still the highest-risk unknown. |
| V6 | No script-execution API exists | **MEASURED — wrong, or at least premature.** A whole script API surface exists. See §2. |

**Paths (MEASURED).** `C4D_PATH_LIBRARY_USER` = `…\AppData\Roaming\Maxon\Maxon Cinema 4D 2026_1ABCDC12\library`. Note the **installation hash suffix** (`_1ABCDC12`): the folder name is machine-specific, so paths must always be resolved through `c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY_USER)` and never constructed from a version string. Scripts and plugins are `…\library\scripts` and `…\library\plugins`.

**Symbols (MEASURED).** All 15 symbols §7 depends on are present: `CommandData`, `RegisterCommandPlugin`, `GeDialog`, `GeUserArea`, `TreeViewFunctions`, `CUSTOMGUI_TREEVIEW`, `DLG_TYPE_ASYNC`, `C4DThread`, `GeGetC4DPath`, `GetActiveDocument`, `EventAdd`, `BaseBitmap`, `MessageDialog`, `QuestionDialog`, `GeUpdateUI`. The architecture is buildable as designed.

---

## 2. The script API surface (new — probe 2 pending)

Probe 1's V6 scan found that C4D already models scripts as first-class objects:

- **Callables:** `c4d.LoadPythonScript`, `c4d.CreateNewPythonScript`, `c4d.GetScriptHead`, `c4d.GetDynamicScriptID`, `c4d.SetActiveScriptObject`
- **Container schema:** `PYTHONSCRIPT_SCRIPTPATH`, `PYTHONSCRIPT_TEXT`, `PYTHONSCRIPT_SCRIPTNAME`, `PYTHONSCRIPT_SCRIPTHELP`, `PYTHONSCRIPT_SHOWINMENU`, `PYTHONSCRIPT_SCRIPTENABLE`, `PYTHONSCRIPT_ADDEVENT`
- **Metadata constants:** `SCRIPTMETA_NAME`, `SCRIPTMETA_DOCUMENTATION`
- **Identity/registry:** `ID_SCRIPTFOLDER`, `ID_PYTHONSCRIPT`, `IDENTIFYFILE_SCRIPT`, `SCRIPT_CONTEXT_SCRIPT_MANAGER`
- **Messages:** `MSG_SCRIPT_EXECUTE`, `MSG_INVOKE_SCRIPT_FUNCTION`, `MSG_MULTI_SCRIPTINFO`, `MSG_SCRIPT_RETRIEVEBITMAP`
- **Process helpers:** `c4d.storage.GeExecuteFile`, `c4d.storage.GeExecuteProgram`

Two consequences, both material:

1. **`GetScriptHead` + `SCRIPTMETA_NAME` / `SCRIPTMETA_DOCUMENTATION` suggest C4D already has a script-header convention.** If so, §6 should adopt it rather than invent `# @title:` / `# @desc:`. Inventing a second convention alongside a native one would be a mistake.
2. **`LoadPythonScript` and `MSG_SCRIPT_EXECUTE` may make the hand-rolled runner in §3 unnecessary** — or at least give a supported path with correct undo behaviour for free.

`tools/phase0_probe2_scriptapi.py` introspects all of this. **Run it before writing any runner code.** It is read-only by default; `CALL_LOAD_PYTHON_SCRIPT` is opt-in because that call's signature is unknown and it may replace Script Manager editor contents.

`GeExecuteFile` / `GeExecuteProgram` also replace the planned `os.startfile` / `open -R` branching for "open in editor" and "reveal in file browser" with something cross-platform and native.

---

## 3. Runner specification (corrected by probe 1)

```
run(script_path):
  src = read fresh from disk          # never cache; the file may have changed
  ns  = {
    "__name__": "__main__",           # MEASURED: matches Script Manager
    "__file__": script_path,          # Script Manager sets the string
                                      # 'scriptmanager'; a real path is strictly
                                      # better and breaks nothing
    "doc": c4d.documents.GetActiveDocument(),
    "op":  doc.GetActiveObject(),
  }
  # Do NOT inject c4d — MEASURED: Script Manager does not, and every script
  # imports it itself.
  sys.path.insert(0, dirname(script_path))   # sibling imports; restore in finally
  try:
      exec(compile(src, script_path, "exec"), ns)
      # Do NOT call main(). See below.
  except Exception:
      traceback -> C4D console + panel status line; never kill the dialog
  finally:
      restore sys.path
      c4d.EventAdd()
```

**The `main()` correction.** v2 of this plan specified "call `main()` if defined". That was wrong twice over:

- **MEASURED:** Script Manager does *not* call `main()` automatically. Probe 1 defined `main()` and never called it; it never ran.
- All four scripts in this repo end with `if __name__ == '__main__': main()`, and `__name__` **is** `'__main__'`. So they self-call — and a runner that also called `main()` would have **executed every one of them twice**. For `Batch_Current_State_to_Object.py` that means duplicating every generated object.

Correct behaviour is to replicate Script Manager exactly: set `__name__`, exec, and stop. A script that defines `main()` without calling it does not run under Script Manager either, so fidelity is the right target.

**Still open — undo (V5).** If C4D does not wrap our `exec` the way it wraps Script Manager execution, the runner must wrap it; wrapping when C4D already does produces nested, broken undo. `UNDOTYPE_NEW = 44` is `MEASURED`. This is the one remaining answer that can cost a user real work.

**Compatibility gate:** the four existing scripts must run unchanged. That is Phase 2's acceptance test.

---

## 4. The "smart" layer

Categories plus tags alone is a file browser. These earn the build:

1. **Frecency ranking** — `frequency × recency` decay. Highest value per line of code.
2. **Command palette** — one hotkey, type three characters, `Enter` runs. Likely beats the browser panel for daily use; consider shipping it first.
3. **Fuzzy / subsequence matching** — `fmn` matches `Fix_Mixamo_Names`.
4. **Auto-tagging via AST** — derive tags from imports and attribute chains (`c4d.modules.mograph`, `BaseObject`, `CTrack`). Zero authoring effort on the initial library.
5. **Context-awareness** — boost or disable entries against scene state. Note `op` is `None` when nothing is selected (`MEASURED`), so preconditions must handle that.
6. **Destructive guard** — confirm before running scripts marked destructive.
7. **Parameters (stretch)** — a declared parameter spec generates a small dialog, so one script replaces a family of near-duplicates.

---

## 5. Indexing — safety and performance

**Safety rule (non-negotiable): indexing must never import or exec a script.** Read the text, parse with `ast.parse`, extract the header. Scanning a folder must never run code. This rules out "import the module and read `__tags__`".

**Budget:** cold scan of 1000 scripts < 2 s; warm open < 100 ms. Cache key `(path, mtime, size)`; re-parse only on change. If the cold scan misses budget, move it to a `C4DThread` (`MEASURED` present) and populate progressively rather than blocking the UI.

**Collisions:** key by absolute path; disambiguate same-named scripts in the UI by parent folder.

---

## 6. Metadata — pending §2

Source of truth = an inline header in each script: travels with the file, survives moves, diffs in git, shared for free on clone. That remains the argument for §0 option A.

**But the exact header syntax is now blocked on probe 2.** If `GetScriptHead` / `SCRIPTMETA_*` define a native convention, adopt it and extend it only where it falls short (tags, category, preconditions). Only invent a `# @key: value` grammar if there is nothing native to build on.

Either way: unknown keys ignored (forward-compatible); missing header degrades gracefully to filename + folder path, since **none of the four existing scripts has one**. Runtime fields (`run_count`, `last_run`, `favorite`) live only in the index, keyed by path, never written back into source.

---

## 7. Architecture

```
plugin/
  script_browser.pyp          # CommandData registration + dialog wiring
  core/                       # zero c4d imports — testable anywhere
    scanner.py                # walk roots, mtime cache, incremental reindex
    metadata.py               # header parse + ast auto-tagging
    model.py                  # Script / Category / Tag / Library dataclasses
    store.py                  # index.json + settings.json, schema migration
    search.py                 # fuzzy match + filters + frecency rank
  ui/
    panel.py                  # GeDialog: tree + list + search + actions
    palette.py                # command palette
    meta_editor.py            # header editor
  runner.py                   # §3
  res/                        # icons, strings
```

`core/` ↔ `c4d` separation is the main testability decision: all logic runs under plain pytest with no C4D present.

**Dockability:** open with `GeDialog.Open(c4d.DLG_TYPE_ASYNC, pluginid, …)` and implement `CommandData.RestoreLayout()`, or the docked panel vanishes on restart.

**Storage:** `index.json` + `settings.json` under the resolved user library path, both carrying `"schema": 1` and a migration function from day one.

---

## 8. Plugin IDs (procurement blocker — start now)

- IDs must be **registered at developers.maxon.net** against your Maxon account. Arbitrary IDs collide with other plugins and corrupt prefs. **Only you can request these.**
- Need: 1 for the CommandData, 1 for the palette, plus a reserved block (~50–100) for hotkey slots.
- **Per-script hotkeys** need one registered `CommandData` ID each, registered at plugin-load time. Design: a fixed block of slot IDs; the user assigns *script → slot*; the slot binds in Command Manager like any command. Assignments persist in `settings.json`. (Probe 2 checks `GetDynamicScriptID`, which may offer a supported alternative.)

---

## 9. Testing

| Layer | Method | Runs where |
|---|---|---|
| `core/` | pytest, fixtures from `scripts/` | anywhere, incl. CI |
| runner semantics | probes 1 and 2 | manual, in C4D |
| `c4d`-touching code | `c4dpy` (`ASSUME` needs a license) or a stubbed `c4d` | dev machine |
| UI | manual smoke checklist, versioned in repo | in C4D |

Add a GitHub Action running pytest on `core/` — the only part testable automatically.

---

## 10. UX

Search focused on open · type-to-filter · ↑/↓ navigate · `Enter` run · `Ctrl+Enter` open in editor · `Esc` clear then close · `Ctrl+F` favourite. Sort: frecency (default) / name / recent / category. Tag chips click-to-filter, shift-click to AND.

Errors surface in three places: C4D console (full traceback), panel status line (one line), rolling log file.

Reveal-in-folder and open-in-editor go through `c4d.storage.GeExecuteFile` / `GeExecuteProgram` (`MEASURED` present) rather than per-OS branching.

---

## 11. Phases and acceptance criteria

| Phase | Deliverable | Done when |
|---|---|---|
| **0** | `tools/phase0_probe.py`, `tools/phase0_probe2_scriptapi.py` | V1–V4, V6 done. **Remaining: V5 undo, and probe 2's verdict on whether §3's runner is needed at all.** |
| **1** | `core/` + tests | pytest green; indexes the four headerless scripts; 1000-script cold scan < 2 s |
| **2** | Panel + palette + runner | all four scripts run unchanged and exactly once; undo is a single step; panel docks and survives restart |
| **3** | Tags, filters, favourites, frecency, metadata editor | any script in a 30-script library found in < 3 keystrokes |
| **4** | Auto-tag, preconditions, destructive guard, hotkey slots, thumbnails | a Command Manager hotkey fires a script |
| **5** (stretch) | Parameter dialogs | one parameterised script replaces a family |

---

## 12. Repo restructure (Phase 1)

Move the four scripts into `scripts/<Category>/` and add headers. Fix `List_Hiearchy.py` → `List_Hierarchy.py`. Rename `OpenPose Sequence Generator From Selected Joints.py` (spaces complicate paths and shortcuts). Rewrite `README.md`, which currently documents only the hierarchy printer. Keep `plugin/` and `scripts/` separate so the plugin releases independently.

---

## 13. Distribution

Folder (`ScriptBrowser/script_browser.pyp` + `res/`), zipped per release; install by dropping into the plugins dir and restarting. `ASSUME` 2024/2025 work too if all are Python 3.11 — claim it only after testing each.

---

## 14. Open questions

1. **§0 first**: is the Asset Browser already enough? (an hour of hands-on before building)
2. **V5**: press Ctrl+Z twice in the probe scene and report which nulls vanish.
3. **Probe 2**: does `LoadPythonScript` execute or merely load? Does `GetScriptHead` define a native metadata convention?
4. Index roots: native scripts folder, this repo, or configurable? (recommend configurable, seeded with both)
5. Ship the command palette before the browser panel?
6. Target 2026 only, or 2024/2025 as well?
