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
_ALL_CONSONANT_PENALTY = 3.0  # leave of 2+ tiles with no vowel
_ALL_VOWEL_PENALTY = 5.0  # leave of 2+ tiles with no consonant (worse)
_Q_WITHOUT_U_PENALTY = 8.0  # holding Q with no U and no blank to unload it


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
            value -= _ALL_CONSONANT_PENALTY
        elif vowels == real:
            value -= _ALL_VOWEL_PENALTY

    # A Q with no way to unload it (no U and no blank) is a liability.
    if counts.get("Q", 0) and not counts.get("U", 0) and not counts.get(BLANK, 0):
        value -= _Q_WITHOUT_U_PENALTY

    return round(value, 2)


_TUNABLE_DEFAULTS = {
    "blank": 25.0,
    "s": 8.0,
    "e": 4.0,
    "duplicate_penalty": 2.0,
    "all_vowel_penalty": 5.0,
    "all_consonant_penalty": 3.0,
    "q_without_u_penalty": 8.0,
}


def apply_params(params: dict) -> None:
    """Reset the tunable leave weights to defaults, then apply overrides from ``params``.

    Used by the offline tuner (tune_leaves.py). Keys: blank, s, e, duplicate_penalty,
    all_vowel_penalty, all_consonant_penalty, q_without_u_penalty. Calling with ``{}``
    restores the shipped defaults, so the function is idempotent between trials.
    """
    global _DUPLICATE_PENALTY, _ALL_VOWEL_PENALTY, _ALL_CONSONANT_PENALTY, _Q_WITHOUT_U_PENALTY
    p = {**_TUNABLE_DEFAULTS, **(params or {})}
    _TILE_VALUE["?"] = float(p["blank"])
    _TILE_VALUE["S"] = float(p["s"])
    _TILE_VALUE["E"] = float(p["e"])
    _DUPLICATE_PENALTY = float(p["duplicate_penalty"])
    _ALL_VOWEL_PENALTY = float(p["all_vowel_penalty"])
    _ALL_CONSONANT_PENALTY = float(p["all_consonant_penalty"])
    _Q_WITHOUT_U_PENALTY = float(p["q_without_u_penalty"])
