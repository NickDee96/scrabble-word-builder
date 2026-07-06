"""Golden + equivalence tests for :mod:`scrabble_engine`.

These lock in correct behavior for the new anagram-signature engine:

* **Equivalence** – for racks *without* blanks, the new engine must return exactly
  the same ``(word, score)`` set as the original permutation-based algorithm (a copy
  of which lives here as ``_reference_builder``). This proves the fast rewrite did not
  change results.
* **Correctness** – explicit tests cover the bugs the old engine had: multiple blanks
  collapsing to the same letter, and blank-aware scoring.
"""
import itertools

import pytest

from scrabble_engine import (
    SCORES,
    WORDS,
    find_words,
    is_valid_word,
    word_score,
)


# --------------------------------------------------------------------------- #
# Reference implementation: the ORIGINAL permutation algorithm (no-blank path).
# Used only to prove the new engine is equivalent for racks without blanks.
# --------------------------------------------------------------------------- #
def _reference_score(word):
    return sum(SCORES.get(c.upper(), 0) for c in word)


def _reference_builder(letters, board_letters):
    letters = [x.upper() for x in letters]
    board_letters = "".join(x.upper() for x in board_letters)
    out = set()
    for i in range(1, len(letters) + 1):
        for subset in itertools.permutations(letters, i):
            subset = list(subset)
            for j in range(len(subset) + 1):
                word = "".join(subset[:j] + list(board_letters) + subset[j:])
                if word in WORDS:
                    out.add((word, _reference_score(word)))
    return out


# --------------------------------------------------------------------------- #
# Equivalence (no blanks)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "rack, board",
    [
        ("CAT", ""),
        ("DOG", ""),
        ("STAR", ""),
        ("RETAIL", ""),
        ("WERTASH", ""),
        ("S", "CAT"),
        ("ES", "CAR"),
        ("ED", "PLANN"),
    ],
)
def test_matches_reference_without_blanks(rack, board):
    assert set(find_words(rack, board)) == _reference_builder(rack, board)


# --------------------------------------------------------------------------- #
# Blank-tile correctness (the old engine got these wrong)
# --------------------------------------------------------------------------- #
def test_single_blank_scores_zero():
    with_tile = dict(find_words("CAT"))
    with_blank = dict(find_words("CA "))  # trailing space = one blank
    assert with_tile["CAT"] == 5           # C(3)+A(1)+T(1)
    assert with_blank["CAT"] == 4          # T supplied by a blank -> 0


def test_question_mark_is_also_a_blank():
    assert dict(find_words("CA?"))["CAT"] == 4


def test_multiple_blanks_can_be_different_letters():
    # "AND" needs N and D from two DIFFERENT blanks. The old engine forced every
    # blank to the same replacement letter and would miss this entirely.
    results = dict(find_words("A  "))  # A + two blanks
    assert "AND" in results
    assert results["AND"] == 1  # only A scores; both blanks score 0


def test_blank_never_makes_score_negative():
    for word, score in find_words("?? "):  # three blanks
        assert score >= 0


# --------------------------------------------------------------------------- #
# Board letters must be contiguous
# --------------------------------------------------------------------------- #
def test_board_letters_are_contiguous():
    results = dict(find_words("S", "CAT"))
    assert results["CATS"] == 6      # C+A+T+S
    assert "SCAT" in results         # "CAT" is contiguous
    assert "CAST" not in results     # "CAT" is NOT contiguous in CAST


def test_board_letters_score_at_face_value():
    # Board "CAR" (C3+A1+R1=5) plus an S tile -> CARS scores 6.
    assert dict(find_words("S", "CAR"))["CARS"] == 6


# --------------------------------------------------------------------------- #
# Result shape / invariants
# --------------------------------------------------------------------------- #
def test_results_sorted_by_score_desc():
    scores = [score for _, score in find_words("WERTASH")]
    assert scores == sorted(scores, reverse=True)


def test_no_duplicate_words():
    words = [word for word, _ in find_words("WERTASH")]
    assert len(words) == len(set(words))


def test_empty_rack_returns_nothing():
    assert find_words("") == []


def test_case_insensitive():
    assert set(find_words("cat")) == set(find_words("CAT"))


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #
def test_is_valid_word():
    assert is_valid_word("cat")
    assert is_valid_word("QUIZ")
    assert not is_valid_word("zzzzz")
    assert not is_valid_word("")


def test_word_score():
    assert word_score("QUIZ") == 22       # Q10+U1+I1+Z10
    assert word_score("CAT") == 5
    assert word_score("CAT", [2]) == 4    # blank at index 2 (T) scores 0
