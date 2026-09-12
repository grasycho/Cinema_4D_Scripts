"""The command palette: hotkey, type three characters, Enter.

DESIGN.md section 4.6 calls this the highest daily value of the whole project,
and at 18 scripts it probably is. It is deliberately thinner than the panel —
no tags, no detail editor, no scopes. One field, a short ranked list, Enter.
"""

from __future__ import annotations

from typing import List

import c4d
from c4d import gui

import registry
from ui.state import Browser

GRP_RESULTS = 2001

ID_SEARCH = 2010
ID_HINT = 2011

ID_ROW = 2100
MAX_ROWS = 8


class PaletteDialog(gui.GeDialog):
    """Type-and-run, with no chrome in the way."""

    def __init__(self):
        super(PaletteDialog, self).__init__()
        self.browser = Browser()
        self.rows: List[registry.ScriptEntry] = []
        self.query = ""

    def CreateLayout(self):
        self.SetTitle("Run Script")
        self.GroupBegin(0, c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT, cols=1)
        self.GroupBorderSpace(8, 8, 8, 8)
        self.AddEditText(ID_SEARCH, c4d.BFH_SCALEFIT)
        self.AddStaticText(ID_HINT, c4d.BFH_SCALEFIT, name="Type to filter, Enter to run the top hit.")
        self.GroupBegin(GRP_RESULTS, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=1)
        self.GroupEnd()
        self.GroupEnd()
        return True

    def InitValues(self):
        # Fresh every time it opens: the Script Manager may have changed.
        self.browser.refresh()
        self.query = ""
        self.SetString(ID_SEARCH, "")
        self.rebuild()
        self.Activate(ID_SEARCH)
        return True

    def rebuild(self):
        self.rows = self.browser.results(self.query)[:MAX_ROWS]
        self.LayoutFlushGroup(GRP_RESULTS)
        for index, script in enumerate(self.rows):
            label = ("> " if index == 0 else "   ") + script.name
            self.AddButton(ID_ROW + index, c4d.BFH_SCALEFIT, name=label)
        self.LayoutChanged(GRP_RESULTS)

    def Message(self, msg, result):
        if msg.GetId() == c4d.BFM_ACTION and msg.GetInt32(c4d.BFM_ACTION_ID) == ID_SEARCH:
            query = self.GetString(ID_SEARCH)
            if query != self.query:
                self.query = query
                self.rebuild()
        return super(PaletteDialog, self).Message(msg, result)

    def Command(self, cid, msg):
        if cid == ID_SEARCH:
            # Enter in the field: run the top hit and get out of the way.
            self.query = self.GetString(ID_SEARCH)
            self.rebuild()
            if self.rows:
                self.browser.run(self.rows[0])
                self.Close()
            return True

        index = cid - ID_ROW
        if 0 <= index < len(self.rows):
            self.browser.run(self.rows[index])
            self.Close()
        return True
