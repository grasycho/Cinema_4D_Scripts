"""A minimum ``c4d`` stand-in, so the registry walk can be tested off-machine.

It models only what ``registry.py`` touches, with the ids and behaviour probe 3
measured (DESIGN.md section 2). It proves the tree walk, the empty-path filter
and the folder paths are right; it proves nothing about C4D itself, which still
needs the manual smoke checklist.
"""

from __future__ import annotations

import types

ID_PYTHONSCRIPT = 1026256
ID_SCRIPTFOLDER = 1026688

PYTHONSCRIPT_SCRIPTPATH = 1000
PYTHONSCRIPT_TEXT = 1001

C4D_PATH_LIBRARY_USER = 3


class Container(object):
    def __init__(self, values):
        self.values = values

    def GetString(self, key):
        return self.values.get(key, "")


class Node(object):
    """A ``BaseList2D`` as far as the walk is concerned."""

    def __init__(self, name, node_type, path="", text="", children=None):
        self.name = name
        self.node_type = node_type
        self.container = Container(
            {PYTHONSCRIPT_SCRIPTPATH: path, PYTHONSCRIPT_TEXT: text}
        )
        self.children = list(children or [])
        self.next = None
        for first, second in zip(self.children, self.children[1:]):
            first.next = second

    def GetName(self):
        return self.name

    def GetType(self):
        return self.node_type

    def GetDataInstance(self):
        return self.container

    def GetDown(self):
        return self.children[0] if self.children else None

    def GetNext(self):
        return self.next


class Head(object):
    def __init__(self, roots):
        self.roots = list(roots)
        for first, second in zip(self.roots, self.roots[1:]):
            first.next = second

    def GetFirst(self):
        return self.roots[0] if self.roots else None


def script(name, path, text="x", dynamic_id=0):
    node = Node(name, ID_PYTHONSCRIPT, path=path, text=text)
    node.dynamic_id = dynamic_id
    return node


def folder(name, children):
    return Node(name, ID_SCRIPTFOLDER, children=children)


def install(monkeypatch, roots):
    """Put a fake ``c4d`` in ``sys.modules`` exposing ``roots`` as the tree."""
    module = types.ModuleType("c4d")
    module.ID_PYTHONSCRIPT = ID_PYTHONSCRIPT
    module.ID_SCRIPTFOLDER = ID_SCRIPTFOLDER
    module.PYTHONSCRIPT_SCRIPTPATH = PYTHONSCRIPT_SCRIPTPATH
    module.PYTHONSCRIPT_TEXT = PYTHONSCRIPT_TEXT
    module.C4D_PATH_LIBRARY_USER = C4D_PATH_LIBRARY_USER
    module.calls = []
    module.EventAdd = lambda: None
    module.CallCommand = lambda cid: module.calls.append(cid)

    head = Head(roots)
    module.plugins = types.SimpleNamespace(
        GetScriptHead=lambda: head,
        GetDynamicScriptID=lambda node: getattr(node, "dynamic_id", -1),
        SetActiveScriptObject=lambda node: module.calls.append(("activate", node.GetName())),
    )
    module.storage = types.SimpleNamespace(
        GeGetC4DPath=lambda which: "/library/user",
        GeExecuteFile=lambda path: True,
    )
    module.documents = types.SimpleNamespace(GetActiveDocument=lambda: None)

    monkeypatch.setitem(__import__("sys").modules, "c4d", module)
    return module
