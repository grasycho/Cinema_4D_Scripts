# ============================================================================
# Phase 0 probe 3 — walk C4D's own script registry
#
# Probe 2 established that GetScriptHead() returns a live c4d.GeListHead: C4D
# already maintains a tree of script objects (ID_PYTHONSCRIPT = 1026256) and
# script folders (ID_SCRIPTFOLDER = 1026688), each carrying name, help, path
# and text in its container. GetDynamicScriptID(bl) takes a BaseList2D, which
# suggests every script already has a command ID it can be invoked by.
#
# If all that holds, C4D has already built the index, the category tree, the
# metadata store and the per-script hotkey mechanism that DESIGN.md planned to
# build from scratch.
#
# HOW TO RUN
#   Script Manager, paste, Execute, copy the whole Console output back.
#
# READ-ONLY by default. CALL_COMMAND_TEST is opt-in because it would actually
# RUN one of your scripts.
# ============================================================================

import traceback

import c4d

CALL_COMMAND_TEST = False

PARAMS = (
    ("SCRIPTNAME", c4d.PYTHONSCRIPT_SCRIPTNAME),
    ("SCRIPTHELP", c4d.PYTHONSCRIPT_SCRIPTHELP),
    ("SCRIPTPATH", c4d.PYTHONSCRIPT_SCRIPTPATH),
    ("SHOWINMENU", c4d.PYTHONSCRIPT_SHOWINMENU),
    ("SCRIPTENABLE", c4d.PYTHONSCRIPT_SCRIPTENABLE),
    ("ADDEVENT", c4d.PYTHONSCRIPT_ADDEVENT),
)

TYPE_NAMES = {
    c4d.ID_PYTHONSCRIPT: "PYTHONSCRIPT",
    c4d.ID_SCRIPTFOLDER: "SCRIPTFOLDER",
}


def section(title):
    print("")
    print("=" * 72)
    print(title)
    print("=" * 72)


nodes = []


def dump(node, depth):
    pad = "  " * depth
    try:
        ntype = node.GetType()
    except Exception as exc:
        print("%s! GetType failed: %r" % (pad, exc))
        return
    label = TYPE_NAMES.get(ntype, "type=%s" % ntype)

    try:
        name = node.GetName()
    except Exception:
        name = "<GetName failed>"

    print("%s- [%s] %r" % (pad, label, name))
    nodes.append(node)

    for pname, pid in PARAMS:
        try:
            val = node[pid]
        except Exception as exc:
            print("%s    %-13s ! %s" % (pad, pname, type(exc).__name__))
            continue
        if pname == "SCRIPTNAME" and val == name:
            continue
        if isinstance(val, str) and len(val) > 100:
            val = val[:100] + "... (%d chars)" % len(val)
        print("%s    %-13s = %r" % (pad, pname, val))

    # The text body: present or not? Length only, never the content.
    try:
        text = node[c4d.PYTHONSCRIPT_TEXT]
        print("%s    %-13s = %s" % (
            pad, "TEXT",
            ("%d chars" % len(text)) if isinstance(text, str) else repr(text)))
    except Exception as exc:
        print("%s    %-13s ! %s" % (pad, "TEXT", type(exc).__name__))

    try:
        print("%s    %-13s = %r" % (pad, "dynamicID", c4d.GetDynamicScriptID(node)))
    except Exception as exc:
        print("%s    %-13s ! %s: %s" % (pad, "dynamicID", type(exc).__name__, exc))

    child = node.GetDown()
    while child:
        dump(child, depth + 1)
        child = child.GetNext()


print("")
print("#" * 72)
print("# PHASE 0 PROBE 3 — SCRIPT REGISTRY TREE")
print("#" * 72)

section("Walking GetScriptHead()")
try:
    head = c4d.GetScriptHead()
    print("head: %r" % (head,))
    first = head.GetFirst()
    if not first:
        print("(list head is empty)")
    node = first
    while node:
        dump(node, 0)
        node = node.GetNext()
except Exception:
    traceback.print_exc()

section("Summary")
print("  total nodes walked : %d" % len(nodes))
by_type = {}
for n in nodes:
    try:
        by_type[TYPE_NAMES.get(n.GetType(), str(n.GetType()))] = \
            by_type.get(TYPE_NAMES.get(n.GetType(), str(n.GetType())), 0) + 1
    except Exception:
        pass
for k, v in sorted(by_type.items()):
    print("    %-16s %d" % (k, v))

# ---------------------------------------------------------------------------
section("Can a script be invoked by its dynamic ID?")
print("  This is the question that decides whether DESIGN.md §3's hand-written")
print("  runner is needed at all. If CallCommand(dynamicID) runs the script,")
print("  C4D handles execution AND undo, and the runner can be deleted.")
print("")
if not CALL_COMMAND_TEST:
    print("  SKIPPED. Set CALL_COMMAND_TEST = True to try it.")
    print("  WARNING: this RUNS a script. Pick a harmless one first by setting")
    print("  TARGET_NAME below, and use a scratch scene.")
else:
    TARGET_NAME = "Zero_Out"
    target = None
    for n in nodes:
        try:
            if n.GetType() == c4d.ID_PYTHONSCRIPT and TARGET_NAME in n.GetName():
                target = n
                break
        except Exception:
            pass
    if target is None:
        print("  No script matching %r found." % TARGET_NAME)
    else:
        try:
            cid = c4d.GetDynamicScriptID(target)
            print("  target %r -> id %r" % (target.GetName(), cid))
            print("  CallCommand result: %r" % (c4d.CallCommand(cid),))
            print("  Did it run? Check the scene and the console above.")
        except Exception:
            traceback.print_exc()

print("")
print("PROBE 3 COMPLETE")
