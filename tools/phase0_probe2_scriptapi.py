# ============================================================================
# Phase 0 probe 2 — the script API surface found by probe 1's V6 scan
#
# Probe 1 assumed "no official execute-a-script API". That assumption is now in
# doubt: the c4d namespace exposes LoadPythonScript, CreateNewPythonScript,
# GetScriptHead, GetDynamicScriptID, SetActiveScriptObject, an ID_SCRIPTFOLDER /
# ID_PYTHONSCRIPT pair, a PYTHONSCRIPT_* container schema and SCRIPTMETA_*
# constants. If C4D already models "a script with a name, a path and
# documentation", the plan should use that model instead of inventing one.
#
# HOW TO RUN
#   Script Manager, paste, Execute, copy the whole Console output back.
#
# This probe is READ-ONLY by default: it prints docstrings and constant values
# and lists files. CALL_LOAD_PYTHON_SCRIPT stays False because LoadPythonScript
# has an unknown signature and may replace whatever is open in the Script
# Manager editor — do not enable it with unsaved work in that editor.
# ============================================================================

import importlib
import os
import traceback

import c4d

CALL_LOAD_PYTHON_SCRIPT = False


def section(title):
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


def describe(dotted):
    parts = dotted.split(".")
    try:
        obj = importlib.import_module(parts[0])
    except Exception as exc:
        print("  %-30s import failed: %r" % (dotted, exc))
        return None
    for name in parts[1:]:
        if not hasattr(obj, name):
            print("  %-30s MISSING" % dotted)
            return None
        obj = getattr(obj, name)
    print("  %s" % dotted)
    print("      repr : %r" % (obj,))
    doc = getattr(obj, "__doc__", None)
    if doc:
        for line in str(doc).strip().splitlines():
            print("      | %s" % line)
    else:
        print("      (no docstring)")
    return obj


print("")
print("#" * 72)
print("# PHASE 0 PROBE 2 — SCRIPT API SURFACE")
print("#" * 72)

# ---------------------------------------------------------------------------
section("Script-related callables")
for dotted in (
    "c4d.LoadPythonScript",
    "c4d.CreateNewPythonScript",
    "c4d.GetScriptHead",
    "c4d.GetDynamicScriptID",
    "c4d.SetActiveScriptObject",
    "c4d.storage.GeExecuteFile",
    "c4d.storage.GeExecuteProgram",
):
    describe(dotted)
    print("")

# ---------------------------------------------------------------------------
section("Script-related constants and their values")
groups = ("PYTHONSCRIPT_", "SCRIPTMETA_", "SCRIPT_CONTEXT_", "SCRIPTMODE_")
for prefix in groups:
    names = sorted(n for n in dir(c4d) if n.startswith(prefix))
    print("  --- %s ---" % prefix)
    for n in names:
        try:
            print("    %-42s = %r" % (n, getattr(c4d, n)))
        except Exception as exc:
            print("    %-42s ! %r" % (n, exc))
    print("")

print("  --- singles ---")
for n in (
    "ID_SCRIPTFOLDER",
    "ID_PYTHONSCRIPT",
    "IDENTIFYFILE_SCRIPT",
    "MSG_SCRIPT_EXECUTE",
    "MSG_INVOKE_SCRIPT_FUNCTION",
    "MSG_MULTI_SCRIPTINFO",
    "MSG_SCRIPT_RETRIEVEBITMAP",
    "SCRIPT_LANGUAGE_PYTHON",
):
    try:
        print("    %-42s = %r" % (n, getattr(c4d, n)))
    except Exception as exc:
        print("    %-42s ! %r" % (n, exc))

# ---------------------------------------------------------------------------
# Does GetScriptHead read metadata out of a script file? If so it may already
# define the header convention DESIGN.md §6 was going to invent.
# ---------------------------------------------------------------------------
section("GetScriptHead behaviour")
user_lib = None
try:
    user_lib = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY_USER)
    print("  user library : %s" % user_lib)
except Exception:
    traceback.print_exc()

scripts_dir = os.path.join(user_lib, "scripts") if user_lib else None
print("  scripts dir  : %s" % scripts_dir)
print("  exists       : %s" % (os.path.isdir(scripts_dir) if scripts_dir else "n/a"))

found = []
if scripts_dir and os.path.isdir(scripts_dir):
    for root, _dirs, files in os.walk(scripts_dir):
        for fn in files:
            if fn.lower().endswith(".py"):
                found.append(os.path.join(root, fn))
print("  .py files    : %d" % len(found))
for p in found[:15]:
    print("     %s" % p)

print("")
print("  Calling GetScriptHead with different argument shapes:")
attempts = [("no args", ())]
if found:
    attempts.append(("script path", (found[0],)))
for label, args in attempts:
    try:
        print("    %-14s -> %r" % (label, c4d.GetScriptHead(*args)))
    except Exception as exc:
        print("    %-14s ! %s: %s" % (label, type(exc).__name__, exc))

print("")
print("  GetDynamicScriptID:")
for label, args in (("no args", ()), ("0", (0,))):
    try:
        print("    %-14s -> %r" % (label, c4d.GetDynamicScriptID(*args)))
    except Exception as exc:
        print("    %-14s ! %s: %s" % (label, type(exc).__name__, exc))

# ---------------------------------------------------------------------------
section("LoadPythonScript (opt-in)")
if not CALL_LOAD_PYTHON_SCRIPT:
    print("  SKIPPED. Set CALL_LOAD_PYTHON_SCRIPT = True to try it.")
    print("  It may replace the Script Manager editor contents — save first.")
    print("  The question it answers: does it EXECUTE a .py file, or only load")
    print("  it into the editor? That decides whether the runner in DESIGN.md")
    print("  §3 is needed at all.")
elif not found:
    print("  No .py files found in the user scripts dir to try it on.")
else:
    target = found[0]
    print("  target: %s" % target)
    try:
        print("  result: %r" % (c4d.LoadPythonScript(target),))
    except Exception:
        traceback.print_exc()
    print("  Now check: did the script RUN, or did it just open in the editor?")

# ---------------------------------------------------------------------------
section("Plugin / script folder registry")
for n in ("ID_SCRIPTFOLDER", "ID_PYTHONSCRIPT"):
    try:
        pid = getattr(c4d, n)
        plug = c4d.plugins.FindPlugin(pid, c4d.PLUGINTYPE_ANY)
        print("  FindPlugin(%s=%r) -> %r" % (n, pid, plug))
    except Exception as exc:
        print("  FindPlugin(%s) ! %s: %s" % (n, type(exc).__name__, exc))

print("")
print("  Script-ish entries in the plugin list:")
try:
    for entry in (c4d.plugins.FilterPluginList(c4d.PLUGINTYPE_COMMAND, True) or []):
        name = entry.GetName()
        if "script" in name.lower():
            print("    %-40s id=%s" % (name, entry.GetID()))
except Exception as exc:
    print("    ! %s: %s" % (type(exc).__name__, exc))

print("")
print("PROBE 2 COMPLETE")
