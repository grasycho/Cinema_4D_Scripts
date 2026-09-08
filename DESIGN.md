# Smart Script Browser — Cinema 4D 2026 Plugin (Research & Plan)

Status: planning, **v4 — re-scoped after Phase 0**. Probes 1–3 have run against the real install.
Target: **Cinema 4D 2026.3.0.4** (`GetC4DVersion() = 2026304`), Windows, Python 3.11.4.

Legend: `MEASURED` = confirmed on the target machine. `OPEN` = still unanswered.

---

## 0. What Phase 0 changed

The plan began as "build a script index with categories, tags, metadata, a runner and a hotkey system." Probing the real application showed **C4D already provides most of that**. The project is now much smaller and should be built *on top of* C4D's registry, not beside it.

| v1–v3 planned to build | Phase 0 finding |
|---|---|
| `scanner.py` — walk folders, mtime cache, incremental reindex | **Delete.** `GetScriptHead()` is a live tree C4D maintains (§2) |
| `Category` model | **Delete.** `ID_SCRIPTFOLDER` nodes already form the tree |
| `Script` model | **Thin.** `ID_PYTHONSCRIPT` nodes carry name, path, source |
| `runner.py` (§3) | **Probably delete** — pending the one `OPEN` question |
| §8 reserved plugin-ID block for hotkeys | **Delete.** `GetDynamicScriptID` already assigns per-script IDs |
| Performance budget: 1000 scripts, < 2 s cold scan | **Delete.** The library is 18 scripts; there is no scan |
| Native metadata to adopt for tags/descriptions | **Wrong** — see the correction in §3 |

What genuinely remains missing from C4D, and is therefore the whole product: **tags, fuzzy search, ranking, descriptions, and a keyboard-driven panel.**

---

## 1. Environment (probe 1)

| # | Assumption | Result |
|---|---|---|
| V1 | Python 3.11 | **Correct.** `3.11.4 (MSC v.1929 64-bit)` |
| V2 | No Qt bundled | **Correct.** PySide6/PySide2/PyQt6/PyQt5/shiboken6/tkinter all absent. UI must be `c4d.gui`; PySide6 only for an out-of-app companion tool |
| V3 | Script Manager calls `main()` | **WRONG — it does not.** All four repo scripts self-call via `if __name__ == '__main__'`, so a runner that also called `main()` would have run each **twice** |
| V4 | `doc`, `op`, `c4d` injected | **Partly wrong.** Injected globals are exactly `__builtins__`, `__file__`, `__name__`, `doc`, `op`. `c4d` is **not** injected. `__file__ == 'scriptmanager'`, a literal string, not a path |
| V5 | C4D auto-wraps execution in undo | **OPEN**, and now low priority — moot if §3 is deleted |
| V6 | No script-execution API exists | **Wrong.** See §2 |

**Paths.** `C4D_PATH_LIBRARY_USER` carries an installation hash (`Maxon Cinema 4D 2026_1ABCDC12`), so paths must always come from `GeGetC4DPath` — never built from a version string.

**Symbols.** All 15 symbols the UI needs are present (`CommandData`, `GeDialog`, `GeUserArea`, `TreeViewFunctions`, `CUSTOMGUI_TREEVIEW`, `DLG_TYPE_ASYNC`, `C4DThread`, …).

---

## 2. C4D's native script registry (probes 2–3) — `MEASURED`

`GetScriptHead()` returns a live `c4d.GeListHead`. Walking it with `GetFirst()` / `GetNext()` / `GetDown()` yields the complete tree:

```
[SCRIPTFOLDER] …\library\scripts              dynamicID = -1
  [PYTHONSCRIPT] Add Character Definition…    dynamicID = 600000013   TEXT 2018 chars
  [PYTHONSCRIPT] Auto_T_Pose_Recovery…        dynamicID = 600000014   TEXT 4902 chars
  [SCRIPTFOLDER] Batch Image To Plane MS      dynamicID = -1
    [PYTHONSCRIPT] Batch Image To Plane MS    dynamicID = 600000015   TEXT 4279 chars
  …
[PYTHONSCRIPT] untitled                       dynamicID = 600000053   SCRIPTPATH = ''
```

18 script nodes, 7 folder nodes, 25 total. Nesting is arbitrary-depth and recursion works.

**Per node:** `GetName()` (the display name), `GetType()` (`ID_PYTHONSCRIPT` 1026256 / `ID_SCRIPTFOLDER` 1026688), `PYTHONSCRIPT_SCRIPTPATH` (absolute path), `PYTHONSCRIPT_TEXT` (full source, in memory), `GetDynamicScriptID(node)` (command ID; `-1` for folders).

Three findings that matter:

**1. The `PYTHONSCRIPT_*` metadata fields are all empty — correction.** After probe 2 I said native metadata gave us "name + help + path" and that §6 should adopt it. That was wrong. Probe 3 read every node: `SCRIPTNAME`, `SCRIPTHELP`, `SHOWINMENU`, `SCRIPTENABLE`, `ADDEVENT` are **`None` on every single node**. Only `SCRIPTPATH` and `TEXT` are populated. Those constants evidently belong to the Python Generator / Python Tag objects, not to Script Manager entries. **There is no native place to store a description, and no native header convention to adopt.** Descriptions and tags are entirely ours to design and store.

**2. `dynamicID` looks positional, which is a risk.** IDs run `600000013 … 600000029` in exact tree-walk order, contiguous. That strongly suggests they are assigned by traversal index at load, not persisted per script. If so, **adding, deleting or renaming a script shifts every subsequent ID**, and any Command Manager hotkey bound to one would silently start firing a different script. This must be tested before hotkeys are built on it (§7). If IDs are unstable, hotkeys go back to being hard.

**3. The tree contains unsaved editor buffers.** The `untitled` node has `SCRIPTPATH = ''` and 5322 chars of text — the Script Manager's open buffer. Any consumer must filter nodes with an empty path, or the panel will list phantom entries.

**Also available:** `SetActiveScriptObject` (display a script in Script Manager — i.e. "open in editor"), `GeExecuteFile` / `GeExecuteProgram` (cross-platform open/reveal, replacing per-OS branching), `LoadPythonScript`, `CreateNewPythonScript` (both untested, both probably unnecessary now).

---

## 3. Execution — one question left

`OPEN`, and it is the last blocking unknown: **does `c4d.CallCommand(GetDynamicScriptID(node))` run the script?**

- **If yes** — delete `runner.py` entirely. C4D executes the script through its own command path, which means correct `doc`/`op` injection, correct `main()` semantics, and correct undo, all for free. V5 stops mattering.
- **If no** — fall back to the hand-rolled runner, corrected per V3/V4: set `__name__ = '__main__'`, set `__file__` to the real path, inject `doc` and `op` but **not** `c4d`, `exec` the source, **do not call `main()`**, restore `sys.path`, `EventAdd()`. And V5 becomes blocking again.

`tools/phase0_probe3_scripttree.py` has this behind `CALL_COMMAND_TEST` (default off, since it runs a real script). Flip it on a scratch scene.

---

## 4. What to actually build

Layered over the native registry, not replacing it:

1. **Panel** — `GeDialog` + `TreeViewCustomGui`, mirroring the registry tree, with a search field.
2. **Fuzzy search** — `fmn` matches `Fix_Mixamo_Names`. At 18 scripts this alone is most of the value.
3. **Tags** — the one thing C4D has no answer for. Stored by us, keyed by absolute path.
4. **Descriptions** — likewise ours, since `SCRIPTHELP` is dead.
5. **Favourites + frecency** — cheap once tags exist, though with 18 scripts ranking matters far less than it would at 500.
6. **Command palette** — hotkey, type, `Enter`. Plausibly the highest daily value; consider shipping it first.
7. **Duplicate detection** — see §5.

Dropped from earlier versions as over-built for this library: AST auto-tagging, `@needs` preconditions, parameter dialogs, thumbnails. Revisit only if the library grows.

---

## 5. The problem the library actually shows

The registry contains two clear duplicate pairs:

- `OpenPose Sequence Generator From Selected Joints` — **17981 chars**
- `OpenPose_Sequence_Generator_From_Selected_Joints` — **21495 chars**

Different sizes: these are two *versions*, not two copies. Same story with `Mixamo_Helper_06` and `Universal_Rig_Normalizer_v3` — version numbers in filenames. And `Fix_Mixamo_Names.py` exists both here and in the C4D library.

**No amount of tagging fixes "which of these two is current?"** A tag browser would let you find both faster and still not tell you which to run. So a small, concrete feature earns its place: flag same-stem scripts, show size/mtime/diff, offer to archive one. That may be worth more than the tagging system.

---

## 6. Metadata storage

Since nothing native exists (§2, finding 1):

- **Tags, descriptions, favourites, run counts** live in one `library.json` under the resolved user library path, keyed by **absolute script path**, carrying `"schema": 1` and a migration function.
- **Sidecar files by basename** carry per-script icon and description — see §6a. Header parsing, where used, must be `ast` / plain text: **indexing must never import or exec a script.**
- Paths as keys are fragile across moves. Acceptable at this scale; note it and re-key on rename when detected.

### 6a. Prior art — the user's own After Effects launcher

[`Script-Launcher-for-After-Effects`](https://github.com/grasycho/Script-Launcher-for-After-Effects) (`ScriptLauncher v4`) is this exact product, already built and shipped for After Effects. It should be treated as the reference design, because matching it gives one mental model across both applications rather than two.

What it already settled, and this plan should follow:

| ScriptLauncher v4 convention | Consequence for the C4D plugin |
|---|---|
| **Icon = image file with the same basename** (`MyScript.jsx` → `MyScript.png`) | Adopt verbatim. Replaces the invented `@icon:` header key |
| **Description = `.txt` file with the same basename**, first line used as the tooltip | **Adopt verbatim.** This replaces the invented `# @desc:` header entirely — the user already has a convention, and it needs no file parsing at all |
| **Favourites + Recent tabs**, with a configurable recent count | Simpler than the frecency ranking in §4, and already proven in daily use. Ship favourites/recent first; treat ranking as optional |
| **Settings in a JSON file beside the tool** | Matches `library.json`; keep the same shape where practical |
| **Execution wrapped in a single undo group** (`app.beginUndoGroup`) | The AE side deliberately makes each run one undo step. The C4D runner should give the same guarantee — which is what V5 is asking |
| Custom scripts folder, chosen in a settings dialog | Confirms the configurable-roots decision |
| Dual list / icon-grid view, as-you-type search | Directly reusable UI model |

**Tags are the one thing ScriptLauncher does not have.** Combined with §5, that sharpens the C4D plugin's purpose: match the launcher the user already knows, then add the tagging and duplicate-detection it lacks — rather than designing a different tool.

---

## 7. Architecture

```
plugin/
  script_browser.pyp      # CommandData + dialog wiring
  core/                   # zero c4d imports — plain pytest
    tags.py               # library.json load/save/migrate
    search.py             # fuzzy match + filter + rank
    dupes.py              # same-stem detection (§5)
  ui/
    panel.py              # GeDialog + TreeView + search
    palette.py            # command palette
  registry.py             # c4d-bound: walk GetScriptHead, filter empty paths
```

No `scanner.py`, no `model.py`, no `store.py` for the index, and probably no `runner.py`. Two registered plugin IDs needed (panel + palette) rather than a reserved block of ~100 — **unless `dynamicID` proves unstable**, in which case per-script hotkeys need rethinking from scratch.

Dockability still requires `CommandData.RestoreLayout()`, or the panel vanishes on restart.

---

## 8. Testing

`core/` is C4D-free and runs under pytest anywhere, including CI — worth a GitHub Action. `registry.py` and the UI need manual verification in C4D against a versioned smoke checklist.

---

## 9. Phases

| Phase | Deliverable | Done when |
|---|---|---|
| **0** | probes 1–3 | Two answers left: `CallCommand` execution, and `dynamicID` stability |
| **1** | `registry.py` + `core/search.py` + read-only panel | panel lists all 18 scripts in tree order, phantom `untitled` filtered, fuzzy search works, double-click runs |
| **2** | Tags, descriptions, favourites, `library.json` | tag the library and find any script in < 3 keystrokes |
| **3** | Command palette | hotkey → 3 chars → `Enter` runs |
| **4** | Duplicate detection (§5) | the two OpenPose versions are surfaced with sizes and dates |
| **5** | Per-script hotkeys | **only if `dynamicID` proves stable** |

---

## 10. Repo cleanup (independent of the plugin)

Fix `List_Hiearchy.py` → `List_Hierarchy.py`. Rename `OpenPose Sequence Generator From Selected Joints.py` (spaces complicate paths and shortcuts) and reconcile it against the two library versions.

`README.md` — **done on `main`.** An earlier revision of this plan claimed it "documents only the hierarchy printer"; that was wrong. It carried sections for three of the four scripts, appended without an index. It has been restructured with an intro and contents table, all existing text preserved, and `Batch_Current_State_to_Object.py` documented for the first time. One discrepancy surfaced and is now flagged in the README: the OpenPose notes describe **v4.1** while the script file header reads **v4.5**.

---

## 11. Open questions

1. **`CallCommand(dynamicID)` — does it run the script?** Decides whether §3 exists at all. Flip `CALL_COMMAND_TEST` in probe 3 on a scratch scene.
2. **Is `dynamicID` stable?** Add a script, restart C4D, re-run probe 3, compare IDs. Decides whether per-script hotkeys are feasible.
3. **Is this a search problem or a duplication problem (§5)?** Honest answer may make §4's tag system secondary to §4.7.
4. Still worth an hour in the Asset Browser before building anything.
5. Ship the command palette before the panel?
