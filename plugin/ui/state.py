"""The controller both the panel and the palette drive.

It joins three things: C4D's registry (``registry.py``), our own metadata
(``core.tags``) and the ranking in ``core.search``. Keeping it here means the
two dialogs share one notion of "what is currently on screen".
"""

from __future__ import annotations

import time
from typing import List, Optional, Sequence, Tuple

import registry
from core import dupes, search, sidecars
from core.tags import Entry, Library, normalise_key

SCOPE_ALL = 0
SCOPE_FAVOURITES = 1
SCOPE_RECENT = 2
SCOPE_DUPLICATES = 3

RECENT_LIMIT = 10


class Browser(object):
    """Live view over the script library."""

    def __init__(self):
        self.entries: List[registry.ScriptEntry] = []
        self.library = Library()
        self._library_path = ""
        self.refresh()

    # -- loading ---------------------------------------------------------

    def refresh(self) -> None:
        """Re-read C4D's registry and our metadata from disk."""
        self.entries = registry.load()
        self._library_path = registry.library_json_path()
        try:
            self.library = Library.load(self._library_path)
        except ValueError:
            # A library written by a newer plugin: refuse to guess at it and
            # keep running read-only rather than overwriting the user's data.
            print("Script Browser: %s has a newer schema; metadata disabled" % self._library_path)
            self.library = Library()
            self._library_path = ""

    def _save(self) -> None:
        if self._library_path:
            self.library.save(self._library_path)

    # -- metadata --------------------------------------------------------

    def entry_meta(self, script: registry.ScriptEntry) -> Entry:
        return self.library.get(script.path)

    def description(self, script: registry.ScriptEntry) -> str:
        """Our stored description, else the same-basename ``.txt`` sidecar."""
        stored = self.entry_meta(script).description
        return stored or sidecars.read_description(script.path)

    def tooltip(self, script: registry.ScriptEntry) -> str:
        text = self.description(script)
        first = text.splitlines()[0].strip() if text else ""
        tags = self.entry_meta(script).tags
        parts = [part for part in (first, ", ".join(tags), script.path) if part]
        return "\n".join(parts)

    def icon(self, script: registry.ScriptEntry) -> Optional[str]:
        return sidecars.find_icon(script.path)

    def all_tags(self) -> Tuple[str, ...]:
        return self.library.all_tags()

    # -- search ----------------------------------------------------------

    def _haystack(self, script: registry.ScriptEntry) -> str:
        """What a query is matched against: name, folder, tags, description."""
        meta = self.entry_meta(script)
        parts = [script.name, script.folder, " ".join(meta.tags), meta.description]
        return " ".join(part for part in parts if part)

    def _scoped(self, scope: int) -> List[registry.ScriptEntry]:
        if scope == SCOPE_FAVOURITES:
            keys = set(self.library.favourites())
            return [item for item in self.entries if normalise_key(item.path) in keys]
        if scope == SCOPE_RECENT:
            order = self.library.recent(limit=RECENT_LIMIT)
            by_key = {normalise_key(item.path): item for item in self.entries}
            return [by_key[key] for key in order if key in by_key]
        if scope == SCOPE_DUPLICATES:
            flagged = set()
            for group in self.duplicates():
                for info in group.scripts:
                    flagged.add(normalise_key(info.path))
            return [item for item in self.entries if normalise_key(item.path) in flagged]
        return list(self.entries)

    def results(self, query: str, scope: int = SCOPE_ALL) -> List[registry.ScriptEntry]:
        """Scripts to show, best match first.

        Recent keeps its own newest-first order when no query narrows it;
        anything else falls back to the fuzzy ranking.
        """
        pool = self._scoped(scope)
        if not query:
            if scope == SCOPE_RECENT:
                return pool
            return sorted(pool, key=lambda item: item.name.lower())
        ranked = search.search(query, pool, key=self._haystack)
        return [result.item for result in ranked]

    def duplicates(self) -> List[dupes.DuplicateGroup]:
        return dupes.find_duplicates(item.as_info() for item in self.entries)

    # -- actions ---------------------------------------------------------

    def run(self, script: registry.ScriptEntry) -> bool:
        """Execute a script and record the run."""
        ok = registry.run(script)
        if ok:
            self.library.record_run(script.path, time.time())
            self._save()
        return ok

    def toggle_favourite(self, script: registry.ScriptEntry) -> bool:
        state = self.library.toggle_favourite(script.path).favourite
        self._save()
        return state

    def set_tags(self, script: registry.ScriptEntry, tags: Sequence[str]) -> None:
        self.library.set_tags(script.path, tags)
        self._save()

    def set_description(self, script: registry.ScriptEntry, text: str) -> None:
        self.library.set_description(script.path, text)
        self._save()
