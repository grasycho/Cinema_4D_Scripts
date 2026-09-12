"""Persistent per-script metadata (DESIGN.md section 6).

C4D stores nothing usable: every ``PYTHONSCRIPT_*`` metadata field is empty on
every node (probe 3), so tags, descriptions, favourites and run counts are
ours to keep. They live in one ``library.json`` keyed by absolute script path.

Paths as keys are fragile across moves; ``Library.rekey`` handles the rename
case when the caller detects one.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Iterable, Optional

SCHEMA = 1


@dataclass(frozen=True)
class Entry:
    """Everything we store about one script."""

    tags: tuple[str, ...] = ()
    description: str = ""
    favourite: bool = False
    run_count: int = 0
    last_run: float = 0.0

    def is_empty(self) -> bool:
        return self == Entry()


def normalise_key(path: str) -> str:
    """Canonical ``library.json`` key for a script path."""
    return os.path.normcase(os.path.abspath(path))


def normalise_tags(tags: Iterable[str]) -> tuple[str, ...]:
    """Lowercase, strip, de-duplicate and sort, so tag sets compare equal."""
    return tuple(sorted({tag.strip().lower() for tag in tags if tag.strip()}))


def migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Bring a loaded document up to the current schema.

    Schema 1 is the first, so this only guards against absent or future
    versions; add a branch per bump.
    """
    version = data.get("schema")
    if version is None:
        data = {"schema": SCHEMA, "entries": data.get("entries", {})}
        version = SCHEMA
    if version > SCHEMA:
        raise ValueError(f"library.json schema {version} is newer than {SCHEMA}")
    return data


def _entry_from_dict(raw: dict[str, Any]) -> Entry:
    return Entry(
        tags=normalise_tags(raw.get("tags", ())),
        description=str(raw.get("description", "")),
        favourite=bool(raw.get("favourite", False)),
        run_count=int(raw.get("run_count", 0)),
        last_run=float(raw.get("last_run", 0.0)),
    )


@dataclass
class Library:
    """The in-memory view of ``library.json``."""

    entries: dict[str, Entry] = field(default_factory=dict)

    # -- persistence ------------------------------------------------------

    @classmethod
    def load(cls, path: str) -> "Library":
        """Read ``path``. A missing or unreadable file yields an empty library."""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        data = migrate(data)
        entries = {}
        for key, raw in (data.get("entries") or {}).items():
            if isinstance(raw, dict):
                entries[normalise_key(key)] = _entry_from_dict(raw)
        return cls(entries)

    def save(self, path: str) -> None:
        """Write ``path`` atomically, dropping entries that carry no data."""
        document = {
            "schema": SCHEMA,
            "entries": {
                key: asdict(entry)
                for key, entry in sorted(self.entries.items())
                if not entry.is_empty()
            },
        }
        directory = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(directory, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=directory, delete=False, suffix=".tmp"
        )
        try:
            with handle:
                json.dump(document, handle, indent=2, sort_keys=True)
            os.replace(handle.name, path)
        except BaseException:
            try:
                os.unlink(handle.name)
            except OSError:
                pass
            raise

    # -- reads ------------------------------------------------------------

    def get(self, path: str) -> Entry:
        """The entry for ``path``, or a blank one. Never raises."""
        return self.entries.get(normalise_key(path), Entry())

    def all_tags(self) -> tuple[str, ...]:
        return tuple(sorted({tag for entry in self.entries.values() for tag in entry.tags}))

    def favourites(self) -> tuple[str, ...]:
        return tuple(sorted(key for key, entry in self.entries.items() if entry.favourite))

    def recent(self, limit: int = 10) -> tuple[str, ...]:
        """Paths most recently run, newest first."""
        run = [(key, entry) for key, entry in self.entries.items() if entry.last_run > 0]
        run.sort(key=lambda item: (-item[1].last_run, item[0]))
        return tuple(key for key, _ in run[:limit])

    def with_tag(self, tag: str) -> tuple[str, ...]:
        wanted = tag.strip().lower()
        return tuple(sorted(key for key, entry in self.entries.items() if wanted in entry.tags))

    # -- writes -----------------------------------------------------------

    def _update(self, path: str, **changes: Any) -> Entry:
        key = normalise_key(path)
        entry = replace(self.entries.get(key, Entry()), **changes)
        if entry.is_empty():
            self.entries.pop(key, None)
        else:
            self.entries[key] = entry
        return entry

    def set_tags(self, path: str, tags: Iterable[str]) -> Entry:
        return self._update(path, tags=normalise_tags(tags))

    def add_tag(self, path: str, tag: str) -> Entry:
        return self.set_tags(path, self.get(path).tags + (tag,))

    def remove_tag(self, path: str, tag: str) -> Entry:
        wanted = tag.strip().lower()
        return self.set_tags(path, [t for t in self.get(path).tags if t != wanted])

    def set_description(self, path: str, description: str) -> Entry:
        return self._update(path, description=description.strip())

    def set_favourite(self, path: str, favourite: bool) -> Entry:
        return self._update(path, favourite=bool(favourite))

    def toggle_favourite(self, path: str) -> Entry:
        return self.set_favourite(path, not self.get(path).favourite)

    def record_run(self, path: str, when: float) -> Entry:
        entry = self.get(path)
        return self._update(path, run_count=entry.run_count + 1, last_run=float(when))

    def rekey(self, old_path: str, new_path: str) -> Optional[Entry]:
        """Move an entry after a rename. Returns the moved entry, if any."""
        old_key = normalise_key(old_path)
        entry = self.entries.pop(old_key, None)
        if entry is None:
            return None
        self.entries[normalise_key(new_path)] = entry
        return entry
