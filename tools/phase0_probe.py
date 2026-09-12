# ============================================================================
# Phase 0 probe — Cinema 4D script-execution environment
#
# Settles assumptions V1-V6 in DESIGN.md. Run this BEFORE writing runner code.
#
# HOW TO RUN
#   1. Open a SCRATCH scene (Ctrl+N) — see the warning below.
#   2. Extensions > Script Manager, paste this file, Execute.
#   3. Open the Console (Shift+F10) and copy the ENTIRE output back.
#   4. Then do the manual undo steps the V5 section prints, and report those.
#
# WARNING: with RUN_UNDO_TEST = True this inserts two Null objects named
# PROBE_A_* / PROBE_B_* into the ACTIVE document. That is the only way to
# measure undo behaviour. Set it to False to skip, but then V5 stays open —
# and V5 is the assumption most likely to cost a user their work if wrong.
# ============================================================================

# MUST be the first executable statement: captures what C4D injected before
# this script defines anything of its own. This is the V4 measurement.
_INJECTED_GLOBALS = sorted(globals().keys())

RUN_UNDO_TEST = True

import importlib
import os
import platform
import sys
import traceback


def section(title):
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


def resolve(dotted):
    """Resolve 'c4d.gui.GeDialog' without raising. Returns (found, detail)."""
    parts = dotted.split(".")
    try:
        obj = importlib.import_module(parts[0])
    except Exception as exc:
        return False, "import failed: %r" % (exc,)
    for name in parts[1:]:
        if not hasattr(obj, name):
            return False, "missing at '%s'" % name
        obj = getattr(obj, name)
    return True, type(obj).__name__


print("")
print("#" * 72)
print("# CINEMA 4D PHASE 0 PROBE")
print("#" * 72)

# ---------------------------------------------------------------------------
# V1 — interpreter
# ---------------------------------------------------------------------------
section("V1  Python interpreter")
try:
    print("sys.version      : %s" % sys.version.replace("\n", " "))
    print("version_info     : %s" % (tuple(sys.version_info),))
    print("platform         : %s" % platform.platform())
    print("executable       : %s" % sys.executable)
    print("sys.path entries : %d" % len(sys.path))
except Exception:
    traceback.print_exc()

# ---------------------------------------------------------------------------
# V2 — GUI toolkit availability (decides the entire UI stack)
# ---------------------------------------------------------------------------
section("V2  Qt binding availability")
for mod in ("PySide6", "PySide2", "PyQt6", "PyQt5", "shiboken6", "tkinter"):
    try:
        importlib.import_module(mod)
        print("  %-12s AVAILABLE" % mod)
    except Exception as exc:
        print("  %-12s no  (%s)" % (mod, type(exc).__name__))

# ---------------------------------------------------------------------------
# V4 — what Script Manager injects into the namespace
# ---------------------------------------------------------------------------
section("V4  Injected globals (captured before this script defined anything)")
print("names: %s" % (_INJECTED_GLOBALS,))
print("")
for name in ("__name__", "__file__", "__doc__", "__package__"):
    print("  %-12s = %r" % (name, globals().get(name, "<NOT DEFINED>")))
print("")
for name in ("doc", "op", "c4d", "tp"):
    val = globals().get(name, "<NOT DEFINED>")
    print("  %-12s = %r" % (name, val))
    if name == "doc" and val != "<NOT DEFINED>" and val is not None:
        try:
            print("               doc name: %r" % val.GetDocumentName())
        except Exception as exc:
            print("               (GetDocumentName failed: %r)" % (exc,))

# ---------------------------------------------------------------------------
# c4d module facts
# ---------------------------------------------------------------------------
section("C4D version and paths")
try:
    import c4d

    for fn in ("GetC4DVersion", "GetMachineFeatures"):
        if hasattr(c4d, fn):
            try:
                if fn == "GetC4DVersion":
                    print("  c4d.%s() = %s" % (fn, c4d.GetC4DVersion()))
            except Exception as exc:
                print("  c4d.%s() failed: %r" % (fn, exc))

    print("")
    print("  Resolved C4D_PATH_* locations:")
    path_consts = sorted(n for n in dir(c4d) if n.startswith("C4D_PATH_"))
    if not path_consts:
        print("    (no C4D_PATH_* constants found on c4d)")
    for name in path_consts:
        try:
            resolved = c4d.storage.GeGetC4DPath(getattr(c4d, name))
            print("    %-34s = %s" % (name, resolved))
        except Exception as exc:
            print("    %-34s ! %s" % (name, type(exc).__name__))
except Exception:
    traceback.print_exc()

# ---------------------------------------------------------------------------
# Symbols the planned architecture depends on (§7)
# ---------------------------------------------------------------------------
section("Symbol availability (DESIGN.md §7 dependencies)")
for dotted in (
    "c4d.plugins.CommandData",
    "c4d.plugins.RegisterCommandPlugin",
    "c4d.gui.GeDialog",
    "c4d.gui.GeUserArea",
    "c4d.gui.TreeViewFunctions",
    "c4d.gui.MessageDialog",
    "c4d.gui.QuestionDialog",
    "c4d.gui.GeUpdateUI",
    "c4d.CUSTOMGUI_TREEVIEW",
    "c4d.DLG_TYPE_ASYNC",
    "c4d.threading.C4DThread",
    "c4d.storage.GeGetC4DPath",
    "c4d.documents.GetActiveDocument",
    "c4d.EventAdd",
    "c4d.bitmaps.BaseBitmap",
):
    ok, detail = resolve(dotted)
    print("  %-40s %s  %s" % (dotted, "OK " if ok else "MISSING", detail))

# ---------------------------------------------------------------------------
# Asset API — decides DESIGN.md §0 option B
# ---------------------------------------------------------------------------
section("Asset API availability (§0 build-vs-reuse decision)")
for dotted in (
    "maxon.AssetInterface",
    "maxon.AssetDescriptionInterface",
    "maxon.KeywordAssetInterface",
    "maxon.CategoryAssetInterface",
    "maxon.AssetDataBasesInterface",
):
    ok, detail = resolve(dotted)
    print("  %-40s %s  %s" % (dotted, "OK " if ok else "MISSING", detail))

# ---------------------------------------------------------------------------
# V6 — is there an official "execute a .py file" entry point?
# ---------------------------------------------------------------------------
section("V6  Search for a script-execution API")
needles = ("script", "exec", "runscript", "sourcecode")
try:
    import c4d

    for modname in ("c4d", "c4d.plugins", "c4d.storage", "c4d.documents", "c4d.gui"):
        try:
            mod = importlib.import_module(modname)
        except Exception:
            continue
        hits = [n for n in dir(mod) if any(k in n.lower() for k in needles)]
        print("  %-16s %s" % (modname, hits if hits else "(none)"))
except Exception:
    traceback.print_exc()

# ---------------------------------------------------------------------------
# V5 — undo semantics. THE critical unknown.
# ---------------------------------------------------------------------------
section("V5  Undo behaviour")
if not RUN_UNDO_TEST:
    print("SKIPPED (RUN_UNDO_TEST = False). V5 remains unanswered.")
else:
    try:
        import c4d

        target = globals().get("doc") or c4d.documents.GetActiveDocument()

        undo_new = getattr(c4d, "UNDOTYPE_NEW", None)
        undo_const = "UNDOTYPE_NEW"
        if undo_new is None:
            undo_new = getattr(c4d, "UNDO_NEW", None)
            undo_const = "UNDO_NEW" if undo_new is not None else "<NEITHER FOUND>"
        print("  undo constant in use: %s = %r" % (undo_const, undo_new))

        # A: inserted with NO undo bookkeeping at all.
        a = c4d.BaseObject(c4d.Onull)
        a.SetName("PROBE_A_no_undo_calls")
        target.InsertObject(a)

        # B: inserted with the documented StartUndo/AddUndo/EndUndo pattern.
        b = c4d.BaseObject(c4d.Onull)
        b.SetName("PROBE_B_with_undo_calls")
        target.StartUndo()
        target.InsertObject(b)
        if undo_new is not None:
            target.AddUndo(undo_new, b)
        target.EndUndo()

        c4d.EventAdd()

        print("")
        print("  Inserted PROBE_A_no_undo_calls and PROBE_B_with_undo_calls.")
        print("")
        print("  NOW DO THIS BY HAND AND REPORT:")
        print("    1. Look at the Object Manager. Both nulls present?")
        print("    2. Press Ctrl+Z ONCE.   Which null vanished (A, B, both, neither)?")
        print("    3. Press Ctrl+Z AGAIN.  Which null vanished now?")
        print("    4. Check Edit menu: what does the undo entry say?")
        print("")
        print("  READING THE RESULT:")
        print("    A vanishes without us registering it -> C4D auto-wraps script")
        print("      execution; our runner must NOT add its own undo wrap.")
        print("    A survives, only B undoes -> no auto-wrap; the runner must")
        print("      wrap, and scripts that skip AddUndo are not undoable.")
    except Exception:
        traceback.print_exc()

# ---------------------------------------------------------------------------
# V3 — does Script Manager call main() after executing the module body?
# ---------------------------------------------------------------------------
section("V3  main() convention")
print("  Module body finished.")
print("  If the next line appears, Script Manager called main() by itself.")
print("  If output ends here, it does not — the runner must call main() itself.")


def main():
    # Deliberately never called by this script. Only C4D should trigger it.
    print("")
    print("  >>> V3 RESULT: main() WAS called automatically by Script Manager.")
    print("  >>> __name__ inside main() = %r" % (__name__,))
