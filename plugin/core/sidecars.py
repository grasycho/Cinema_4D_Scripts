"""Same-basename sidecar files (DESIGN.md section 6a).

The user's After Effects launcher already settled this convention: an icon is
an image beside the script with the same basename, and a description is a
``.txt`` beside it with the same basename, whose first line is the tooltip.
Adopted verbatim so both applications behave the same way.

Nothing here imports ``c4d`` and nothing here executes a script.
"""

from __future__ import annotations

import os
from typing import Optional

# Ordered by preference: C4D's bitmap loader handles all of these.
ICON_EXTENSIONS = (".png", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp")

DESCRIPTION_EXTENSION = ".txt"


def _stem(script_path: str) -> str:
    """The script path without its extension."""
    root, _ = os.path.splitext(script_path)
    return root


def find_icon(script_path: str) -> Optional[str]:
    """Path of the icon beside ``script_path``, or ``None``.

    Extensions are tried in ``ICON_EXTENSIONS`` order; the first that exists
    wins, so a hand-made ``.png`` beats a stray ``.bmp``.
    """
    if not script_path:
        return None
    stem = _stem(script_path)
    for extension in ICON_EXTENSIONS:
        candidate = stem + extension
        if os.path.isfile(candidate):
            return candidate
    return None


def description_path(script_path: str) -> str:
    """Path of the ``.txt`` description beside ``script_path``, or ``""``."""
    if not script_path:
        return ""
    candidate = _stem(script_path) + DESCRIPTION_EXTENSION
    return candidate if os.path.isfile(candidate) else ""


def read_description(script_path: str) -> str:
    """Text of the sidecar description, or ``""`` when there is none.

    Unreadable or undecodable files are treated as absent: a description is a
    convenience, never a reason to fail an index.
    """
    path = description_path(script_path)
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read().strip()
    except OSError:
        return ""


def tooltip(script_path: str) -> str:
    """First line of the sidecar description, or ``""``."""
    text = read_description(script_path)
    if not text:
        return ""
    return text.splitlines()[0].strip()
