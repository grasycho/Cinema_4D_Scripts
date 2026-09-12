"""Smart Script Browser — Cinema 4D 2026 plugin entry point.

Registers two commands:

* **Script Browser** — the dockable panel (search, tags, favourites, duplicates)
* **Run Script** — the command palette, worth binding to a hotkey

Install by copying the whole ``plugin`` folder into the C4D ``plugins``
directory, then restart. See ``plugin/README.md``.
"""

import os
import sys

import c4d
from c4d import plugins

# The plugin folder must be importable before ``registry`` or ``ui`` resolve.
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from ui.palette import PaletteDialog  # noqa: E402
from ui.panel import ScriptBrowserDialog  # noqa: E402

# ASSUME: these are development ids. Before distributing the plugin, request a
# real pair at https://developers.maxon.net/ and replace both — colliding ids
# silently break whichever plugin loads second.
PLUGIN_ID_PANEL = 1065001
PLUGIN_ID_PALETTE = 1065002


class ScriptBrowserCommand(plugins.CommandData):
    """Opens the dockable panel and restores it on restart."""

    dialog = None

    def Execute(self, doc):
        if self.dialog is None:
            self.dialog = ScriptBrowserDialog()
        return self.dialog.Open(
            dlgtype=c4d.DLG_TYPE_ASYNC,
            pluginid=PLUGIN_ID_PANEL,
            defaultw=420,
            defaulth=520,
        )

    def RestoreLayout(self, secret):
        # Without this the panel vanishes from the layout on restart.
        if self.dialog is None:
            self.dialog = ScriptBrowserDialog()
        return self.dialog.Restore(pluginid=PLUGIN_ID_PANEL, secret=secret)


class PaletteCommand(plugins.CommandData):
    """Opens the command palette."""

    dialog = None

    def Execute(self, doc):
        if self.dialog is None:
            self.dialog = PaletteDialog()
        return self.dialog.Open(
            dlgtype=c4d.DLG_TYPE_ASYNC,
            pluginid=PLUGIN_ID_PALETTE,
            defaultw=380,
            defaulth=280,
        )

    def RestoreLayout(self, secret):
        if self.dialog is None:
            self.dialog = PaletteDialog()
        return self.dialog.Restore(pluginid=PLUGIN_ID_PALETTE, secret=secret)


if __name__ == "__main__":
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID_PANEL,
        str="Script Browser",
        info=0,
        icon=None,
        help="Search, tag and run the scripts C4D already knows about.",
        dat=ScriptBrowserCommand(),
    )
    plugins.RegisterCommandPlugin(
        id=PLUGIN_ID_PALETTE,
        str="Run Script",
        info=0,
        icon=None,
        help="Command palette: type a few characters, press Enter.",
        dat=PaletteCommand(),
    )
