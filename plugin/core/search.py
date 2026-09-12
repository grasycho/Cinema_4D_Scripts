"""Fuzzy subsequence matching and ranking.

``fmn`` must match ``Fix_Mixamo_Names`` (DESIGN.md section 4.2). Matching is a
subsequence test; ranking rewards matches that start a word, run
consecutively, and appear early.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence

# Score weights. Tuned by eye against the 18-script library; keep them
# integers so scores stay exactly reproducible.
BASE = 10
CONSECUTIVE_BONUS = 8
BOUNDARY_BONUS = 8
CASE_BONUS = 2
GAP_PENALTY = 1
MAX_GAP_PENALTY = 10

WORD_SEPARATORS = "_-. /\\"


@dataclass(frozen=True)
class Match:
    """One successful fuzzy match."""

    score: int
    positions: tuple[int, ...]


def _is_boundary(text: str, index: int) -> bool:
    if index == 0:
        return True
    previous = text[index - 1]
    if previous in WORD_SEPARATORS:
        return True
    # camelCase: a lowercase or digit followed by an uppercase letter.
    return (previous.islower() or previous.isdigit()) and text[index].isupper()


def _char_score(query_char: str, text: str, index: int, consecutive: bool) -> int:
    score = BASE
    if consecutive:
        score += CONSECUTIVE_BONUS
    if _is_boundary(text, index):
        score += BOUNDARY_BONUS
    if query_char == text[index]:
        score += CASE_BONUS
    return score


def _gap_penalty(gap: int) -> int:
    return min(gap, MAX_GAP_PENALTY) * GAP_PENALTY


def match(query: str, text: str) -> Optional[Match]:
    """Return the best-scoring match of ``query`` in ``text``, or ``None``.

    An empty query matches everything with a score of 0. Matching is
    case-insensitive; an exact-case hit scores slightly higher.
    """
    if not query:
        return Match(0, ())
    if not text or len(query) > len(text):
        return None

    lowered_query = query.lower()
    lowered_text = text.lower()

    # best[j] holds (score, positions) for matching query[:i+1] ending exactly
    # at text[j], for the row i currently being built.
    previous_row: list[Optional[tuple[int, tuple[int, ...]]]] = []
    for j, char in enumerate(lowered_text):
        if char == lowered_query[0]:
            score = _char_score(query[0], text, j, consecutive=False) - _gap_penalty(j)
            previous_row.append((score, (j,)))
        else:
            previous_row.append(None)

    for i in range(1, len(lowered_query)):
        current_row: list[Optional[tuple[int, tuple[int, ...]]]] = [None] * len(text)
        for j in range(i, len(lowered_text)):
            if lowered_text[j] != lowered_query[i]:
                continue
            best: Optional[tuple[int, tuple[int, ...]]] = None
            for k in range(i - 1, j):
                candidate = previous_row[k]
                if candidate is None:
                    continue
                score = (
                    candidate[0]
                    + _char_score(query[i], text, j, consecutive=(k == j - 1))
                    - _gap_penalty(j - k - 1)
                )
                if best is None or score > best[0]:
                    best = (score, candidate[1] + (j,))
            current_row[j] = best
        previous_row = current_row

    finals = [entry for entry in previous_row if entry is not None]
    if not finals:
        return None
    score, positions = max(finals, key=lambda entry: entry[0])
    return Match(score, positions)


@dataclass(frozen=True)
class Result:
    """A ranked search hit."""

    item: object
    score: int
    positions: tuple[int, ...] = field(default=())


def _identity(item: object) -> str:
    return str(item)


def search(
    query: str,
    items: Iterable[object],
    key: Callable[[object], str] = _identity,
) -> list[Result]:
    """Rank ``items`` against ``query``, best first.

    An empty query returns every item in input order. Ties break on shorter
    text first, then alphabetically, so results are stable.
    """
    indexed = list(enumerate(items))
    if not query:
        return [Result(item, 0, ()) for _, item in indexed]

    hits: list[tuple[int, int, str, Result]] = []
    for index, item in indexed:
        text = key(item)
        found = match(query, text)
        if found is None:
            continue
        hits.append((found.score, len(text), text, Result(item, found.score, found.positions)))

    hits.sort(key=lambda hit: (-hit[0], hit[1], hit[2]))
    return [hit[3] for hit in hits]


def filter_matching(query: str, items: Sequence[object], key: Callable[[object], str] = _identity) -> list[object]:
    """Ranked items only, without the score and highlight positions."""
    return [result.item for result in search(query, items, key)]
