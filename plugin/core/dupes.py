"""Same-stem duplicate detection (DESIGN.md section 5).

The library holds pairs like ``OpenPose Sequence Generator From Selected
Joints`` / ``OpenPose_Sequence_Generator_From_Selected_Joints`` and
``Universal_Rig_Normalizer_v3`` — different *versions* of one script, not
copies. Tagging cannot answer "which of these is current?"; surfacing the
group with sizes and dates can.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePath
from typing import Iterable

# A trailing version marker: _v3, -V2.1, " 06", _2026.
_VERSION_SUFFIX = re.compile(r"_v?\d+(?:[._]\d+)*$")
_SEPARATORS = re.compile(r"[\s\-.]+")


@dataclass(frozen=True)
class ScriptInfo:
    """The minimum a duplicate check needs about a script."""

    path: str
    name: str
    size: int = 0
    mtime: float = 0.0


@dataclass(frozen=True)
class DuplicateGroup:
    """Scripts sharing a normalised stem, newest first."""

    stem: str
    scripts: tuple[ScriptInfo, ...]


def normalise_stem(name: str) -> str:
    """Reduce a script name to the identity shared by its versions.

    Drops any directory part and ``.py`` suffix, folds separators to ``_``,
    lowercases, and strips one trailing version marker.
    """
    stem = PurePath(name).name
    if stem.lower().endswith(".py"):
        stem = stem[:-3]
    stem = _SEPARATORS.sub("_", stem.strip())
    stem = re.sub(r"_+", "_", stem).strip("_").lower()
    return _VERSION_SUFFIX.sub("", stem).strip("_")


def find_duplicates(scripts: Iterable[ScriptInfo]) -> list[DuplicateGroup]:
    """Group scripts whose normalised stems collide.

    Groups are ordered by stem; within a group the newest file comes first,
    falling back to the larger file when mtimes tie.
    """
    buckets: dict[str, list[ScriptInfo]] = {}
    for script in scripts:
        stem = normalise_stem(script.name or script.path)
        if not stem:
            continue
        buckets.setdefault(stem, []).append(script)

    groups = []
    for stem in sorted(buckets):
        members = buckets[stem]
        if len(members) < 2:
            continue
        members.sort(key=lambda script: (-script.mtime, -script.size, script.path))
        groups.append(DuplicateGroup(stem, tuple(members)))
    return groups
