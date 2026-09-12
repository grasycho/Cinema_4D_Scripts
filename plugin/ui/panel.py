"""The dockable browser panel.

A ``GeDialog`` with a search field, four scopes and a rebuilt list of result
rows. C4D 2026 bundles no Qt (probe 1, V2), so this is plain ``c4d.gui``.

The list is rebuilt with ``LayoutFlushGroup`` / ``LayoutChanged`` rather than
driven by a ``TreeViewCustomGui``: the registry is 18 scripts, a flat ranked
list is what fuzzy search wants anyway, and flushing a group is the least
fragile dynamic layout C4D offers.
"""

from __future__ import annotations

from typing import List

import c4d
from c4d import gui

import registry
from ui.state import (
    SCOPE_ALL,
    SCOPE_DUPLICATES,
    SCOPE_FAVOURITES,
    SCOPE_RECENT,
    Browser,
)

GRP_TOP = 1000
GRP_SCROLL = 1001
GRP_RESULTS = 1003
GRP_DETAIL = 1002

ID_SEARCH = 1010
ID_SCOPE = 1011
ID_REFRESH = 1012
ID_COUNT = 1013

ID_DETAIL_NAME = 1020
ID_DETAIL_PATH = 1021
ID_DETAIL_TAGS = 1022
ID_DETAIL_DESC = 1023
ID_DETAIL_APPLY = 1024
ID_DETAIL_RUN = 1025
ID_DETAIL_EDIT = 1026
ID_DETAIL_REVEAL = 1027
ID_DETAIL_CLOSE = 1028

# One block of ids per column of the result list. 1000 rows is far beyond the
# 18 this library holds, and keeps the blocks from ever colliding.
ROW_STRIDE = 1000
ID_ROW_RUN = 3000
ID_ROW_FAV = ID_ROW_RUN + ROW_STRIDE
ID_ROW_INFO = ID_ROW_FAV + ROW_STRIDE

SCOPE_LABELS = (
    (SCOPE_ALL, "All"),
    (SCOPE_FAVOURITES, "Favourites"),
    (SCOPE_RECENT, "Recent"),
    (SCOPE_DUPLICATES, "Duplicates"),
)

MAX_ROWS = ROW_STRIDE - 1


class ScriptBrowserDialog(gui.GeDialog):
    """Search, run, favourite and tag the scripts C4D already knows about."""

    def __init__(self):
        super(ScriptBrowserDialog, self).__init__()
        self.browser = Browser()
        self.query = ""
        self.scope = SCOPE_ALL
        self.rows: List[registry.ScriptEntry] = []
        self.selected: registry.ScriptEntry = None

    # -- layout ----------------------------------------------------------

    def CreateLayout(self):
        self.SetTitle("Script Browser")

        self.GroupBegin(GRP_TOP, c4d.BFH_SCALEFIT, cols=3, rows=1)
        self.GroupBorderSpace(6, 6, 6, 2)
        self.AddEditText(ID_SEARCH, c4d.BFH_SCALEFIT)
        self.AddComboBox(ID_SCOPE, c4d.BFH_RIGHT)
        for value, label in SCOPE_LABELS:
            self.AddChild(ID_SCOPE, value, label)
        self.AddButton(ID_REFRESH, c4d.BFH_RIGHT, name="Reload")
        self.GroupEnd()

        self.AddStaticText(ID_COUNT, c4d.BFH_SCALEFIT, name="")

        self.ScrollGroupBegin(
            GRP_SCROLL,
            c4d.BFH_SCALEFIT | c4d.BFV_SCALEFIT,
            c4d.SCROLLGROUP_VERT | c4d.SCROLLGROUP_AUTOVERT,
        )
        self.GroupBegin(GRP_RESULTS, c4d.BFH_SCALEFIT | c4d.BFV_TOP, cols=3)
        self.GroupBorderSpace(6, 2, 6, 6)
        self.GroupEnd()
        self.GroupEnd()

        self.GroupBegin(GRP_DETAIL, c4d.BFH_SCALEFIT, cols=1)
        self.GroupBorderSpace(6, 4, 6, 6)
        self.GroupEnd()

        return True

    def InitValues(self):
        self.SetString(ID_SEARCH, "")
        self.SetInt32(ID_SCOPE, SCOPE_ALL)
        self.rebuild()
        return True

    # -- result list -----------------------------------------------------

    def rebuild(self):
        """Re-run the query and redraw the result rows."""
        self.rows = self.browser.results(self.query, self.scope)[:MAX_ROWS]

        self.LayoutFlushGroup(GRP_RESULTS)
        for index, script in enumerate(self.rows):
            favourite = self.browser.entry_meta(script).favourite
            self.AddButton(ID_ROW_FAV + index, c4d.BFH_LEFT, initw=24, name="*" if favourite else "-")
            self.AddButton(ID_ROW_RUN + index, c4d.BFH_SCALEFIT, name=script.name)
            self.AddButton(ID_ROW_INFO + index, c4d.BFH_RIGHT, initw=24, name="i")
        if not self.rows:
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="No scripts match.")
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")
            self.AddStaticText(0, c4d.BFH_SCALEFIT, name="")
        self.LayoutChanged(GRP_RESULTS)

        self.SetString(ID_COUNT, "%d of %d scripts" % (len(self.rows), len(self.browser.entries)))
        self.rebuild_detail()

    def rebuild_detail(self):
        """Redraw the detail editor for the selected script."""
        self.LayoutFlushGroup(GRP_DETAIL)
        script = self.selected
        if script is not None:
            self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2)
            self.AddStaticText(ID_DETAIL_NAME, c4d.BFH_SCALEFIT, name=script.name)
            self.AddButton(ID_DETAIL_CLOSE, c4d.BFH_RIGHT, initw=24, name="x")
            self.GroupEnd()

            self.AddStaticText(ID_DETAIL_PATH, c4d.BFH_SCALEFIT, name=script.path)

            self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2)
            self.AddStaticText(0, c4d.BFH_LEFT, name="Tags")
            self.AddEditText(ID_DETAIL_TAGS, c4d.BFH_SCALEFIT)
            self.AddStaticText(0, c4d.BFH_LEFT, name="Note")
            self.AddEditText(ID_DETAIL_DESC, c4d.BFH_SCALEFIT)
            self.GroupEnd()

            self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=4)
            self.AddButton(ID_DETAIL_RUN, c4d.BFH_SCALEFIT, name="Run")
            self.AddButton(ID_DETAIL_EDIT, c4d.BFH_SCALEFIT, name="Open in editor")
            self.AddButton(ID_DETAIL_REVEAL, c4d.BFH_SCALEFIT, name="Reveal")
            self.AddButton(ID_DETAIL_APPLY, c4d.BFH_SCALEFIT, name="Save")
            self.GroupEnd()

        self.LayoutChanged(GRP_DETAIL)

        if script is not None:
            meta = self.browser.entry_meta(script)
            self.SetString(ID_DETAIL_TAGS, ", ".join(meta.tags))
            self.SetString(ID_DETAIL_DESC, self.browser.description(script).replace("\n", " ").strip())

    # -- events ----------------------------------------------------------

    def Message(self, msg, result):
        """Catch every keystroke in the search field.

        ``Command`` only fires on Enter or focus loss, which is too late for an
        as-you-type list.
        """
        if msg.GetId() == c4d.BFM_ACTION and msg.GetInt32(c4d.BFM_ACTION_ID) == ID_SEARCH:
            query = self.GetString(ID_SEARCH)
            if query != self.query:
                self.query = query
                self.rebuild()
        return super(ScriptBrowserDialog, self).Message(msg, result)

    def Command(self, cid, msg):
        if cid == ID_REFRESH:
            self.browser.refresh()
            self.selected = None
            self.rebuild()
            return True

        if cid == ID_SCOPE:
            self.scope = self.GetInt32(ID_SCOPE)
            self.rebuild()
            return True

        if cid == ID_SEARCH:
            self.query = self.GetString(ID_SEARCH)
            self.rebuild()
            # Enter with exactly one hit is an unambiguous "run that".
            if len(self.rows) == 1:
                self.browser.run(self.rows[0])
            return True

        script = self._row_script(cid, ID_ROW_RUN)
        if script is not None:
            self.browser.run(script)
            if self.scope == SCOPE_RECENT:
                self.rebuild()
            return True

        script = self._row_script(cid, ID_ROW_FAV)
        if script is not None:
            self.browser.toggle_favourite(script)
            self.rebuild()
            return True

        script = self._row_script(cid, ID_ROW_INFO)
        if script is not None:
            self.selected = script
            self.rebuild_detail()
            return True

        return self._detail_command(cid)

    def _row_script(self, cid, base):
        """The script a row button belongs to, or ``None``."""
        index = cid - base
        if 0 <= index < len(self.rows):
            return self.rows[index]
        return None

    def _detail_command(self, cid):
        script = self.selected
        if script is None:
            return True

        if cid == ID_DETAIL_CLOSE:
            self.selected = None
            self.rebuild_detail()
        elif cid == ID_DETAIL_RUN:
            self.browser.run(script)
        elif cid == ID_DETAIL_EDIT:
            registry.open_in_editor(script)
        elif cid == ID_DETAIL_REVEAL:
            registry.reveal(script)
        elif cid == ID_DETAIL_APPLY:
            tags = [part.strip() for part in self.GetString(ID_DETAIL_TAGS).split(",")]
            self.browser.set_tags(script, [tag for tag in tags if tag])
            self.browser.set_description(script, self.GetString(ID_DETAIL_DESC))
            self.rebuild()
        return True
