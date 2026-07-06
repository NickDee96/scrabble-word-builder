"""Golden tests for the board-aware move generator and scorer (board_engine)."""
from board_engine import PlacedTile, generate_moves


def _empty():
    letters = [[None] * 15 for _ in range(15)]
    blanks = [[False] * 15 for _ in range(15)]
    return letters, blanks


def _place(letters, blanks, row, col, word, direction="across", blank_positions=()):
    for i, ch in enumerate(word):
        r = row if direction == "across" else row + i
        c = col + i if direction == "across" else col
        letters[r][c] = ch
        blanks[r][c] = i in blank_positions


def _by_word(moves):
    out = {}
    for m in moves:
        out.setdefault(m.word, m)
    return out


# --------------------------------------------------------------------------- #
# Opening play
# --------------------------------------------------------------------------- #
def test_opening_play_covers_center_and_doubles_word():
    letters, blanks = _empty()
    moves = generate_moves(letters, blanks, "AT")
    words = _by_word(moves)
    assert "AT" in words and "TA" in words
    # Centre (7,7) is a double-word square: (A=1 + T=1) x 2 = 4.
    assert words["AT"].score == 4
    # Every opening play must cover the centre square.
    for m in moves:
        assert any((t.row, t.col) == (7, 7) for t in m.tiles)


def test_opening_bingo_gets_50_point_bonus():
    letters, blanks = _empty()
    moves = generate_moves(letters, blanks, "AEINRST")
    seven = [m for m in moves if len(m.tiles) == 7]
    assert seven, "expected at least one 7-tile opening play"
    # A 7-letter opening covers the centre DWS: min score = sum(1..) x 2 + 50 = 64.
    assert min(m.score for m in seven) >= 64


# --------------------------------------------------------------------------- #
# Hooks / extending existing words
# --------------------------------------------------------------------------- #
def test_prefix_hook_forms_cat():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "AT")  # existing AT across
    moves = generate_moves(letters, blanks, "C")
    words = _by_word(moves)
    assert "CAT" in words
    cat = words["CAT"]
    assert cat.score == 5  # C(3)+A(1)+T(1), no premiums freshly covered
    assert cat.tiles == [PlacedTile(7, 6, "C", False)]


def test_suffix_hook_forms_cats_with_blank_scores_zero():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "CAT")
    moves = generate_moves(letters, blanks, "?")  # single blank
    words = _by_word(moves)
    assert "CATS" in words
    cats = words["CATS"]
    # blank S scores 0: C(3)+A(1)+T(1)+0 = 5
    assert cats.score == 5
    assert cats.tiles[-1].is_blank is True


# --------------------------------------------------------------------------- #
# Cross-word validity
# --------------------------------------------------------------------------- #
def test_invalid_cross_word_is_rejected_valid_is_kept():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "CAT")  # C@(7,7) A@(7,8) T@(7,9)
    moves = generate_moves(letters, blanks, "H")

    # Placing H above A (7,8) makes vertical "HA" (valid) -> allowed.
    assert any(
        PlacedTile(6, 8, "H", False) in m.tiles and m.word == "HA" for m in moves
    )
    # Placing H above C (7,7) would make "HC" (invalid) -> must never appear.
    assert all(all((t.row, t.col) != (6, 7) for t in m.tiles) for m in moves)


def test_lone_incompatible_tile_yields_no_move():
    letters, blanks = _empty()
    letters[7][7] = "Q"  # a lone Q (no valid 2-letter word with a T beside it)
    moves = generate_moves(letters, blanks, "V")
    # QV / VQ and vertical QV / VQ are all invalid -> no legal plays.
    assert moves == []


# --------------------------------------------------------------------------- #
# Leaves + sorting
# --------------------------------------------------------------------------- #
def test_leave_is_reported_and_moves_sorted_by_score():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "CAT")
    moves = generate_moves(letters, blanks, "SE")  # play may use S and/or E
    assert moves == sorted(moves, key=lambda m: (-m.score, m.word))
    cats = next((m for m in moves if m.word == "CATS"), None)
    assert cats is not None
    assert cats.leave == "E"  # played S, kept E
