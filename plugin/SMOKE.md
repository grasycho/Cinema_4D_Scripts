# Smoke checklist — v1

Everything in `tests/` runs off-machine against a fake registry. The dialogs
and the real C4D calls are unverified until this checklist passes inside
Cinema 4D 2026.3.0.4. Record the date and the result; re-run it after any
change to `registry.py` or `ui/`.

## Install

- [ ] Both commands appear in the Command Manager after a restart.
- [ ] Neither registration logs an id collision in the Console.

## Panel

- [ ] Opens, and the list shows every saved script — 18, not 19: the Script
      Manager's `untitled` buffer must not appear.
- [ ] Nested folders resolve, e.g. `Batch Image To Plane MS`.
- [ ] Typing filters the list **as you type**, not only on Enter. If it only
      updates on Enter, `Message`/`BFM_ACTION` is not firing for `ID_SEARCH`.
- [ ] `fmn` puts `Fix_Mixamo_Names` first.
- [ ] Clicking a name runs the script once — **once**, not twice. Twice means
      `CallCommand` ran it and the fallback ran it again.
- [ ] `*` / `-` toggles a favourite, and it survives closing C4D.
- [ ] Recent lists what you just ran, newest first.
- [ ] Duplicates shows the OpenPose pair and the Mixamo_Helper pair.
- [ ] `i` opens the detail editor; Save stores tags and a note; searching for a
      tag finds the script.
- [ ] Open in editor selects the script in the Script Manager.
- [ ] Reveal opens the containing folder.
- [ ] Dock the panel, restart C4D — it comes back. If not, `RestoreLayout` is
      wrong.

## Palette

- [ ] Hotkey opens it with the field already focused.
- [ ] Three characters narrow the list; `Enter` runs the top hit and closes.

## Execution — the open question

`registry.PREFER_CALL_COMMAND` is `True`, so `c4d.CallCommand(dynamicID)` is
tried first and the hand-rolled runner is the fallback.

- [ ] Run a script that prints something. It printed exactly once.
- [ ] The Console shows no `CallCommand(...) failed` line.
- [ ] `Ctrl+Z` undoes the whole run as one step.

If a script runs twice, or does not run at all, `CallCommand` is not the right
path: set `PREFER_CALL_COMMAND = False` and re-run this section. That single
flag is the answer to DESIGN.md open question 1.

## Still open

`dynamicID` stability (DESIGN.md open question 2) is not covered here and gates
Phase 5 only. Add a script, restart, re-run `tools/phase0_probe3_scripttree.py`
and compare the ids. Nothing in the shipped plugin persists a `dynamicID`, so
an unstable id cannot corrupt stored metadata — it would only break per-script
hotkeys, which are not built.

## `library.json`

- [ ] Exists under the user library path after the first favourite.
- [ ] Contains `"schema": 1`.
- [ ] No `.tmp` files left beside it.
