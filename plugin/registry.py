"""C4D's native script registry, read through ``GetScriptHead()``.

Probe 3 (DESIGN.md section 2) established that C4D already maintains a live
tree of ``ID_PYTHONSCRIPT`` / ``ID_SCRIPTFOLDER`` nodes carrying name, absolute
path and full source. This module walks it and hands back plain records; it
never builds an index of its own.

Two measured facts drive the code below:

* every ``PYTHONSCRIPT_*`` metadata field reads ``None``, so nothing here tries
  to read a description or a menu flag off a node;
* the tree contains the Script Manager's unsaved buffers, which have an empty
  ``SCRIPTPATH`` and must be filtered out or the panel lists phantoms.

This is the only module besides ``ui/`` and the ``.pyp`` that imports ``c4d``.
"""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from typing import Iterator, List, Optional

import c4d

from core.dupes import ScriptInfo

# DESIGN.md section 3, open question 1: does CallCommand(dynamicID) actually
# execute the script? If it does, C4D runs it through its own command path and
# gets doc/op injection, main() semantics and undo for free. Until that is
# answered on the real machine, try it first and fall back to the hand-rolled
# runner below, which is corrected per the V3/V4 probe findings.
PREFER_CALL_COMMAND = True


@dataclass(frozen=True)
class ScriptEntry:
    """One executable script in C4D's registry."""

    name: str
    path: str
    dynamic_id: int
    folder: str = ""
    char_count: int = 0

    @property
    def size(self) -> int:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0

    @property
    def mtime(self) -> float:
        try:
            return os.path.getmtime(self.path)
        except OSError:
            return 0.0

    @property
    def exists(self) -> bool:
        return bool(self.path) and os.path.isfile(self.path)

    def as_info(self) -> ScriptInfo:
        """The shape ``core.dupes`` wants."""
        return ScriptInfo(self.path, self.name, self.size, self.mtime)


def _walk(node, folder: str) -> Iterator[ScriptEntry]:
    """Yield every script under ``node``, depth first, in tree order."""
    while node:
        try:
            node_type = node.GetType()
            name = node.GetName()
        except Exception:
            node = node.GetNext()
            continue

        if node_type == c4d.ID_SCRIPTFOLDER:
            child = node.GetDown()
            if child:
                sub = "%s/%s" % (folder, name) if folder else name
                for entry in _walk(child, sub):
                    yield entry
        elif node_type == c4d.ID_PYTHONSCRIPT:
            container = node.GetDataInstance()
            path = ""
            text = ""
            if container is not None:
                path = container.GetString(c4d.PYTHONSCRIPT_SCRIPTPATH) or ""
                text = container.GetString(c4d.PYTHONSCRIPT_TEXT) or ""
            # Unsaved Script Manager buffers have no path; skip them.
            if path:
                try:
                    dynamic_id = c4d.plugins.GetDynamicScriptID(node)
                except Exception:
                    dynamic_id = -1
                yield ScriptEntry(name, path, dynamic_id, folder, len(text))

        node = node.GetNext()


def load() -> List[ScriptEntry]:
    """Every saved script C4D knows about, in tree order."""
    head = c4d.plugins.GetScriptHead()
    if head is None:
        return []
    return list(_walk(head.GetFirst(), ""))


def find(path: str, entries: Optional[List[ScriptEntry]] = None) -> Optional[ScriptEntry]:
    """The entry whose path matches ``path``, or ``None``."""
    if not path:
        return None
    wanted = os.path.normcase(os.path.abspath(path))
    for entry in entries if entries is not None else load():
        if os.path.normcase(os.path.abspath(entry.path)) == wanted:
            return entry
    return None


def read_source(entry: ScriptEntry) -> str:
    """The script's source from disk, falling back to the node's text."""
    try:
        with open(entry.path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _exec_script(entry: ScriptEntry) -> bool:
    """Run a script the way Script Manager does, per the probe findings.

    ``__name__`` is ``'__main__'`` so the repo's own ``if __name__`` guards
    fire, ``__file__`` is the real path (Script Manager passes the literal
    string ``'scriptmanager'``, which is useless to a script), ``doc`` and
    ``op`` are injected but ``c4d`` deliberately is not, and ``main()`` is
    never called — V3 measured that Script Manager does not call it, so calling
    it here would run every guarded script twice.
    """
    source = read_source(entry)
    if not source:
        return False

    document = c4d.documents.GetActiveDocument()
    globals_ = {
        "__name__": "__main__",
        "__file__": entry.path,
        "__builtins__": __builtins__,
        "doc": document,
        "op": document.GetActiveObject() if document else None,
    }

    folder = os.path.dirname(entry.path)
    saved_path = list(sys.path)
    if folder and folder not in sys.path:
        sys.path.insert(0, folder)

    # One run is one undo step, matching the After Effects launcher's
    # beginUndoGroup contract (DESIGN.md section 6a).
    if document:
        document.StartUndo()
    try:
        exec(compile(source, entry.path, "exec"), globals_)
        return True
    except Exception:
        print("Script Browser: %s failed\n%s" % (entry.name, traceback.format_exc()))
        return False
    finally:
        if document:
            document.EndUndo()
        sys.path[:] = saved_path
        c4d.EventAdd()


def run(entry: ScriptEntry) -> bool:
    """Execute ``entry``, preferring C4D's own command path."""
    if PREFER_CALL_COMMAND and entry.dynamic_id > 0:
        try:
            c4d.CallCommand(entry.dynamic_id)
            c4d.EventAdd()
            return True
        except Exception:
            print("Script Browser: CallCommand(%s) failed, running directly" % entry.dynamic_id)
    return _exec_script(entry)


def open_in_editor(entry: ScriptEntry) -> bool:
    """Show the script in the Script Manager."""
    head = c4d.plugins.GetScriptHead()
    if head is None:
        return False
    wanted = os.path.normcase(os.path.abspath(entry.path))

    def locate(node):
        while node:
            if node.GetType() == c4d.ID_PYTHONSCRIPT:
                container = node.GetDataInstance()
                path = container.GetString(c4d.PYTHONSCRIPT_SCRIPTPATH) if container else ""
                if path and os.path.normcase(os.path.abspath(path)) == wanted:
                    return node
            found = locate(node.GetDown())
            if found:
                return found
            node = node.GetNext()
        return None

    node = locate(head.GetFirst())
    if node is None:
        return False
    c4d.plugins.SetActiveScriptObject(node)
    c4d.EventAdd()
    return True


def reveal(entry: ScriptEntry) -> bool:
    """Show the script's folder in Explorer/Finder."""
    folder = os.path.dirname(entry.path)
    if not folder or not os.path.isdir(folder):
        return False
    return bool(c4d.storage.GeExecuteFile(folder))


def library_json_path() -> str:
    """Where ``library.json`` lives.

    ``C4D_PATH_LIBRARY_USER`` carries an installation hash, so the path is
    always resolved through ``GeGetC4DPath`` and never built from a version
    string (DESIGN.md section 1).
    """
    base = c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY_USER)
    return os.path.join(base, "script_browser", "library.json")
