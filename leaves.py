"""Heuristic rack-leave evaluation for equity ranking (Phase 6.C).

:func:`leave_value` estimates the future scoring advantage of keeping ``leave`` on the
rack after a play — i.e. how much the tiles you *keep* are worth for future turns
(bingo potential, flexibility, avoiding clunky tiles).

This is a hand-tuned, license-clean heuristic that needs no data. It captures the
well-established effects: the blank and S are very valuable; Q (especially without a U)
is bad; duplicates are awkward; and badly unbalanced vowel/consonant leaves are weak.
best-play-engine-plan.md describes replacing this with a *learned* table (self-play or
imported) for stronger play — :func:`leave_value` is the single swap-in point.
"""
from collections import Counter

BLANK = "?"
_VOWELS = set("AEIOU")

# Approximate standalone equity value of holding each tile (strategy-informed).
_TILE_VALUE = {
    "?": 25.0, "S": 8.0, "Z": 2.0, "X": 1.5, "E": 4.0, "A": 1.5, "R": 1.5, "T": 1.0,
    "N": 1.0, "I": 0.5, "H": 0.5, "C": 0.5, "D": 0.0, "M": 0.0, "L": 0.0, "P": 0.0,
    "O": -0.5, "K": -0.5, "J": -1.0, "B": -1.0, "G": -1.5, "Y": -1.5, "F": -1.5,
    "W": -2.0, "U": -2.5, "V": -4.0, "Q": -6.0,
}

_DUPLICATE_PENALTY = 2.0  # per extra copy of a letter


def leave_value(leave: str) -> float:
    """Estimated equity value (in points) of keeping ``leave`` on the rack.

    An empty leave (a bingo, all 7 tiles played) is worth 0.
    """
    if not leave:
        return 0.0

    counts = Counter(c.upper() for c in leave)
    value = sum(_TILE_VALUE.get(letter, 0.0) * n for letter, n in counts.items())

    # Duplicates are generally awkward to use.
    for letter, n in counts.items():
        if n > 1 and letter != BLANK:
            value -= (n - 1) * _DUPLICATE_PENALTY

    real = sum(n for letter, n in counts.items() if letter != BLANK)
    vowels = sum(n for letter, n in counts.items() if letter in _VOWELS)
    if real >= 2:
        if vowels == 0:
            value -= 3.0  # all consonants
        elif vowels == real:
            value -= 5.0  # all vowels (worse)

    # A Q with no way to unload it (no U and no blank) is a liability.
    if counts.get("Q", 0) and not counts.get("U", 0) and not counts.get(BLANK, 0):
        value -= 8.0

    return round(value, 2)
