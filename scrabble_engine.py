"""Core word-finding engine for the Scrabble Word Builder.

Shared by the FastAPI service (``app.py``) and the CLI (``scrabble.py``) so there is a
single source of truth for word generation and scoring.

The engine builds an **anagram signature index** once at import time: every dictionary
word is grouped by the sorted tuple of its letters (its *signature*). Finding all
playable words then reduces to enumerating the letter multisets reachable from the rack
(expanding blank tiles) and looking each signature up in O(1) — instead of the old
O(n!) permutation scan.
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict
from itertools import combinations, combinations_with_replacement
from typing import Dict, Iterable, List, Optional, Set, Tuple

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BLANK_CHARS = {" ", "?"}

# Standard Scrabble letter scores.
SCORES: Dict[str, int] = {
    'A': 1, 'B': 3, 'C': 3, 'D': 2, 'E': 1, 'F': 4, 'G': 2, 'H': 4, 'I': 1, 'J': 8,
    'K': 5, 'L': 1, 'M': 3, 'N': 1, 'O': 1, 'P': 3, 'Q': 10, 'R': 1, 'S': 1, 'T': 1,
    'U': 1, 'V': 4, 'W': 4, 'X': 8, 'Y': 4, 'Z': 10,
}

# Backwards-compatible alias for older imports.
scores = SCORES

_DICT_FILENAME = "Collins Scrabble Words (2019).txt"
_DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), _DICT_FILENAME)


def _signature(letters: Iterable[str]) -> str:
    """Return the anagram signature (sorted letters) for a group of letters."""
    return "".join(sorted(letters))


def _load_words(path: str = _DICT_PATH) -> Set[str]:
    """Load the dictionary into an upper-cased set of words."""
    with open(path, "r", encoding="utf-8") as handle:
        return {line.strip().upper() for line in handle if line.strip()}


def _build_index(words: Iterable[str]) -> Dict[str, List[str]]:
    """Group words by their anagram signature for O(1) lookup."""
    index: Dict[str, List[str]] = defaultdict(list)
    for word in words:
        index[_signature(word)].append(word)
    return index


# Loaded once at import time and reused for every request.
WORDS: Set[str] = _load_words()
SIGNATURE_INDEX: Dict[str, List[str]] = _build_index(WORDS)


def word_count() -> int:
    """Number of words in the loaded dictionary."""
    return len(WORDS)


def is_valid_word(word: str) -> bool:
    """Return ``True`` if ``word`` exists in the dictionary."""
    return word.strip().upper() in WORDS


def letter_score(letter: str) -> int:
    """Score for a single letter (0 for blanks / unknown characters)."""
    return SCORES.get(letter.upper(), 0)


def word_score(word: str, zero_indices: Optional[Iterable[int]] = None) -> int:
    """Score ``word``; any positions in ``zero_indices`` (e.g. blank tiles) score 0.

    Retained for backwards compatibility. New code should prefer :func:`find_words`,
    which computes blank-aware scores automatically.
    """
    zeros = set(zero_indices or ())
    return sum(
        0 if i in zeros else SCORES.get(letter.upper(), 0)
        for i, letter in enumerate(word)
    )


def _rack_score(word: str, real: Counter, board: Counter) -> int:
    """Best achievable score for ``word`` given real rack tiles and board letters.

    Board letters and real rack tiles score their face value; any letter that must be
    supplied by a blank scores 0. The blank-covered letters are exactly the per-letter
    shortfall between what the word needs (excluding board letters, which supply
    themselves) and the real tiles available — so the score is unambiguous.
    """
    need = Counter(word) - board  # letters that must come from the rack
    penalty = 0
    for letter, count in need.items():
        deficit = count - real.get(letter, 0)
        if deficit > 0:
            penalty += deficit * SCORES.get(letter, 0)
    full = sum(SCORES.get(letter, 0) for letter in word)
    return full - penalty


def find_words(rack, board_letters: Iterable[str] = "") -> List[Tuple[str, int]]:
    """Find every valid word playable from ``rack`` (optionally through ``board_letters``).

    Args:
        rack: A string or iterable of characters. Spaces and ``?`` are treated as blank
            tiles (wildcards that score 0).
        board_letters: Letters already on the board. They must appear as a contiguous
            block within each returned word and score their face value.

    Returns:
        ``(word, score)`` tuples sorted by descending score, then alphabetically. Each
        word appears once, with its maximum achievable score.
    """
    rack_chars = list(rack)
    real = Counter(c.upper() for c in rack_chars if c.upper() in SCORES)
    n_blanks = sum(1 for c in rack_chars if c in BLANK_CHARS)
    board = "".join(c.upper() for c in board_letters if c.upper() in SCORES)
    board_counter = Counter(board)

    real_tiles = list(real.elements())
    best: Dict[str, int] = {}
    seen_signatures: Set[str] = set()

    # Enumerate every distinct multiset of real rack tiles (any size)...
    for size in range(len(real_tiles) + 1):
        for combo in set(combinations(real_tiles, size)):
            # ...combined with 0..n_blanks wildcard tiles.
            for n_wild in range(n_blanks + 1):
                if size + n_wild == 0:
                    continue  # every word must use at least one rack tile
                for wilds in combinations_with_replacement(ALPHABET, n_wild):
                    signature = _signature(combo + wilds + tuple(board))
                    if signature in seen_signatures:
                        continue
                    seen_signatures.add(signature)
                    for word in SIGNATURE_INDEX.get(signature, ()):
                        if board and board not in word:
                            continue  # board letters must be contiguous
                        score = _rack_score(word, real, board_counter)
                        if word not in best or score > best[word]:
                            best[word] = score

    return sorted(best.items(), key=lambda item: (-item[1], item[0]))


def scrabble_word_builder(letters, board_letters) -> List[Tuple[str, int]]:
    """Backwards-compatible wrapper around :func:`find_words`.

    Preserves the original signature used by the API and CLI.
    """
    return find_words(letters, board_letters)
