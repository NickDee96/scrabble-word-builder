"""Board-aware move generation and scoring for the best-play engine (Phase 6.A/B).

Given a full 15x15 board and a rack, :func:`generate_moves` returns every legal play
(main word + all cross-words valid), each with its correct Scrabble score (premium
squares counted only where tiles are freshly placed, plus cross-word scores and the
50-point bingo bonus).

The generator follows the classic Appel & Jacobson / Gordon approach:
anchor squares + per-square cross-checks + a left-part / extend-right recursion over the
dictionary (here backed by a lazily-built prefix set). This is the correctness-focused
Python prototype; a compiled generator can replace the hot path later (see
best-play-engine-plan.md).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from scrabble_engine import SCORES, WORDS
from leaves import leave_value

BOARD_SIZE = 15
CENTER = (7, 7)
BLANK = "?"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BINGO_BONUS = 50

# Standard English tile distribution (100 tiles). Used for unseen-pool / rack work later.
TILE_DISTRIBUTION: Dict[str, int] = {
    "A": 9, "B": 2, "C": 2, "D": 4, "E": 12, "F": 2, "G": 3, "H": 2, "I": 9, "J": 1,
    "K": 1, "L": 4, "M": 2, "N": 6, "O": 8, "P": 2, "Q": 1, "R": 6, "S": 4, "T": 6,
    "U": 4, "V": 2, "W": 2, "X": 1, "Y": 2, "Z": 1, BLANK: 2,
}

# --- Premium square layout (matches the frontend board) --------------------
_TRIPLE_WORD = {(0, 0), (0, 7), (0, 14), (7, 0), (7, 14), (14, 0), (14, 7), (14, 14)}
_DOUBLE_WORD = {
    (1, 1), (2, 2), (3, 3), (4, 4), (1, 13), (2, 12), (3, 11), (4, 10),
    (13, 1), (12, 2), (11, 3), (10, 4), (13, 13), (12, 12), (11, 11), (10, 10),
    (7, 7),  # center
}
_TRIPLE_LETTER = {
    (1, 5), (1, 9), (5, 1), (5, 5), (5, 9), (5, 13),
    (9, 1), (9, 5), (9, 9), (9, 13), (13, 5), (13, 9),
}
_DOUBLE_LETTER = {
    (0, 3), (0, 11), (2, 6), (2, 8), (3, 0), (3, 7), (3, 14), (6, 2), (6, 6), (6, 8),
    (6, 12), (7, 3), (7, 11), (8, 2), (8, 6), (8, 8), (8, 12), (11, 0), (11, 7),
    (11, 14), (12, 6), (12, 8), (14, 3), (14, 11),
}


def _letter_multiplier(row: int, col: int) -> int:
    if (row, col) in _TRIPLE_LETTER:
        return 3
    if (row, col) in _DOUBLE_LETTER:
        return 2
    return 1


def _word_multiplier(row: int, col: int) -> int:
    if (row, col) in _TRIPLE_WORD:
        return 3
    if (row, col) in _DOUBLE_WORD:
        return 2
    return 1


# --- Lazy DAWG/trie (drives the move-generation recursion) -----------------
class _TrieNode:
    __slots__ = ("children", "is_word")

    def __init__(self) -> None:
        self.children: Dict[str, "_TrieNode"] = {}
        self.is_word = False


_TRIE: Optional["_TrieNode"] = None


def _trie() -> "_TrieNode":
    """Trie of the whole dictionary (built once, on first use).

    Walking child pointers lets the generator branch only into letters that actually
    continue a word - far cheaper than testing every rack letter against a giant prefix
    set, especially for blanks (which would otherwise fan out to all 26 letters).
    """
    global _TRIE
    if _TRIE is None:
        root = _TrieNode()
        for word in WORDS:
            node = root
            for ch in word:
                child = node.children.get(ch)
                if child is None:
                    child = _TrieNode()
                    node.children[ch] = child
                node = child
            node.is_word = True
        _TRIE = root
    return _TRIE


def _walk(node: "_TrieNode", s: str) -> Optional["_TrieNode"]:
    """Descend from ``node`` following the letters of ``s``; ``None`` if no such path."""
    for ch in s:
        node = node.children.get(ch)  # type: ignore[assignment]
        if node is None:
            return None
    return node


Grid = List[List[Optional[str]]]
BoolGrid = List[List[bool]]


@dataclass(frozen=True)
class PlacedTile:
    row: int
    col: int
    letter: str
    is_blank: bool


@dataclass
class Move:
    word: str
    row: int
    col: int
    direction: str  # "across" | "down"
    tiles: List[PlacedTile]
    score: int
    leave: str = ""
    leave_value: float = 0.0
    equity: float = 0.0
    cross_words: List[str] = field(default_factory=list)

    def key(self) -> Tuple:
        """Identity of the physical play (independent of main-word orientation)."""
        return tuple(sorted((t.row, t.col, t.letter, t.is_blank) for t in self.tiles))


def _score_letter(letter: str, is_blank: bool) -> int:
    return 0 if is_blank else SCORES.get(letter, 0)


def _cross_info(
    letters: Grid, blanks: BoolGrid, row: int, col: int
) -> Tuple[Optional[Set[str]], int]:
    """Cross-check for placing a tile at empty (row, col) in a *horizontal* main word.

    Returns (allowed_letters, cross_score) where ``allowed_letters`` is the set of
    letters that form a valid vertical word (or ``None`` meaning "any letter, no
    cross-word"), and ``cross_score`` is the summed value of the existing vertical
    neighbours (0 when there is no cross-word).
    """
    above_parts: List[str] = []
    r = row - 1
    while r >= 0 and letters[r][col] is not None:
        above_parts.append(letters[r][col])  # type: ignore[arg-type]
        r -= 1
    above = "".join(reversed(above_parts))

    below_parts: List[str] = []
    r = row + 1
    while r < BOARD_SIZE and letters[r][col] is not None:
        below_parts.append(letters[r][col])  # type: ignore[arg-type]
        r += 1
    below = "".join(below_parts)

    if not above and not below:
        return None, 0  # no vertical neighbours -> any letter, no cross-word

    cross_score = 0
    r = row - 1
    while r >= 0 and letters[r][col] is not None:
        cross_score += _score_letter(letters[r][col], blanks[r][col])  # type: ignore[arg-type]
        r -= 1
    r = row + 1
    while r < BOARD_SIZE and letters[r][col] is not None:
        cross_score += _score_letter(letters[r][col], blanks[r][col])  # type: ignore[arg-type]
        r += 1

    allowed = {c for c in ALPHABET if (above + c + below) in WORDS}
    return allowed, cross_score


def _transpose(grid: list) -> list:
    return [list(row) for row in zip(*grid)]


def _generate_horizontal(
    letters: Grid, blanks: BoolGrid, rack: str, direction: str, moves: List[Move]
) -> None:
    board_empty = all(letters[r][c] is None for r in range(BOARD_SIZE) for c in range(BOARD_SIZE))
    root = _trie()

    for row in range(BOARD_SIZE):
        # Anchor squares: empty squares adjacent to a tile (or the centre on an empty board).
        anchors: Set[int] = set()
        if board_empty:
            if row == CENTER[0]:
                anchors.add(CENTER[1])
        else:
            for col in range(BOARD_SIZE):
                if letters[row][col] is not None:
                    continue
                neighbours = [
                    (row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1),
                ]
                if any(
                    0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and letters[nr][nc] is not None
                    for nr, nc in neighbours
                ):
                    anchors.add(col)

        if not anchors:
            continue

        cross_cache: Dict[int, Tuple[Optional[Set[str]], int]] = {}

        def cross(col: int) -> Tuple[Optional[Set[str]], int]:
            if col not in cross_cache:
                cross_cache[col] = _cross_info(letters, blanks, row, col)
            return cross_cache[col]

        def record(start_col: int, end_col: int, word: str, placed: List[PlacedTile]) -> None:
            score, cross_words = _score_horizontal(letters, blanks, row, start_col, word, placed, cross)
            r0, c0 = (row, start_col) if direction == "across" else (start_col, row)
            moves.append(
                Move(
                    word=word,
                    row=r0,
                    col=c0,
                    direction=direction,
                    tiles=[_orient(t, direction) for t in placed],
                    score=score,
                    cross_words=cross_words,
                )
            )

        def extend_right(
            col: int,
            node: "_TrieNode",
            prefix: str,
            rack_counter: Counter,
            placed: List[PlacedTile],
            anchor_col: int,
        ) -> None:
            if col < BOARD_SIZE and letters[row][col] is not None:
                existing = letters[row][col]  # type: ignore[assignment]
                child = node.children.get(existing)
                if child is not None:
                    extend_right(col + 1, child, prefix + existing, rack_counter, placed, anchor_col)
                return

            # (row, col) is empty or off-board: we may terminate here.
            if placed and col > anchor_col and node.is_word:
                start_col = col - len(prefix)
                record(start_col, col - 1, prefix, placed)

            if col >= BOARD_SIZE:
                return

            allowed, _cs = cross(col)
            have_blank = rack_counter.get(BLANK, 0) > 0
            for played, child in node.children.items():
                if allowed is not None and played not in allowed:
                    continue
                if rack_counter.get(played, 0) > 0:
                    rack_counter[played] -= 1
                    extend_right(
                        col + 1,
                        child,
                        prefix + played,
                        rack_counter,
                        placed + [PlacedTile(row, col, played, False)],
                        anchor_col,
                    )
                    rack_counter[played] += 1
                if have_blank:
                    rack_counter[BLANK] -= 1
                    extend_right(
                        col + 1,
                        child,
                        prefix + played,
                        rack_counter,
                        placed + [PlacedTile(row, col, played, True)],
                        anchor_col,
                    )
                    rack_counter[BLANK] += 1

        def left_part(
            node: "_TrieNode",
            prefix: str,
            anchor_col: int,
            rack_counter: Counter,
            limit: int,
            placed: List[PlacedTile],
        ) -> None:
            extend_right(anchor_col, node, prefix, rack_counter, placed, anchor_col)
            if limit <= 0:
                return
            left_col = anchor_col - len(prefix) - 1
            if left_col < 0:
                return
            for tile_letter in list(rack_counter):
                if rack_counter[tile_letter] == 0:
                    continue
                candidates = ALPHABET if tile_letter == BLANK else [tile_letter]
                for played in candidates:
                    child = root.children.get(played)
                    if child is None:
                        continue
                    sub = _walk(child, prefix)
                    if sub is None:
                        continue
                    rack_counter[tile_letter] -= 1
                    left_part(
                        sub,
                        played + prefix,
                        anchor_col,
                        rack_counter,
                        limit - 1,
                        [PlacedTile(row, left_col, played, tile_letter == BLANK)] + placed,
                    )
                    rack_counter[tile_letter] += 1

        for anchor_col in anchors:
            rack_counter = Counter(rack)
            if anchor_col > 0 and letters[row][anchor_col - 1] is not None:
                left = anchor_col - 1
                while left > 0 and letters[row][left - 1] is not None:
                    left -= 1
                prefix = "".join(letters[row][left:anchor_col])  # type: ignore[misc]
                node = _walk(root, prefix)
                if node is not None:
                    extend_right(anchor_col, node, prefix, rack_counter, [], anchor_col)
            else:
                limit = 0
                c = anchor_col - 1
                while c >= 0 and letters[row][c] is None and c not in anchors:
                    limit += 1
                    c -= 1
                left_part(root, "", anchor_col, rack_counter, limit, [])


def _orient(tile: PlacedTile, direction: str) -> PlacedTile:
    if direction == "across":
        return tile
    return PlacedTile(tile.col, tile.row, tile.letter, tile.is_blank)


def _score_horizontal(
    letters: Grid,
    blanks: BoolGrid,
    row: int,
    start_col: int,
    word: str,
    placed: List[PlacedTile],
    cross,
) -> Tuple[int, List[str]]:
    placed_cols = {t.col: t for t in placed}
    main_score = 0
    word_mult = 1
    for i, letter in enumerate(word):
        col = start_col + i
        tile = placed_cols.get(col)
        if tile is not None:
            value = _score_letter(letter, tile.is_blank) * _letter_multiplier(row, col)
            word_mult *= _word_multiplier(row, col)
            main_score += value
        else:
            main_score += _score_letter(letter, blanks[row][col])  # type: ignore[arg-type]
    main_score *= word_mult

    total = main_score
    cross_words: List[str] = []
    for tile in placed:
        allowed, cross_score = cross(tile.col)
        if allowed is None:
            continue  # no vertical neighbours -> no cross-word
        letter_value = _score_letter(tile.letter, tile.is_blank) * _letter_multiplier(row, tile.col)
        cross_total = (cross_score + letter_value) * _word_multiplier(row, tile.col)
        total += cross_total
        cross_words.append(_cross_word_string(letters, row, tile.col, tile.letter))

    if len(placed) == 7:
        total += BINGO_BONUS
    return total, cross_words


def _cross_word_string(letters: Grid, row: int, col: int, played: str) -> str:
    parts: List[str] = []
    r = row - 1
    while r >= 0 and letters[r][col] is not None:
        parts.append(letters[r][col])  # type: ignore[arg-type]
        r -= 1
    parts.reverse()
    parts.append(played)
    r = row + 1
    while r < BOARD_SIZE and letters[r][col] is not None:
        parts.append(letters[r][col])  # type: ignore[arg-type]
        r += 1
    return "".join(parts)


def generate_moves(letters: Grid, blanks: BoolGrid, rack: str) -> List[Move]:
    """Return every legal play for ``rack`` on the given board, sorted by score desc.

    ``letters`` is a 15x15 grid of upper-case letters or ``None``; ``blanks`` marks which
    placed board tiles are blanks (worth 0). ``rack`` is a string of A-Z plus ``?`` for
    blank tiles.
    """
    rack = "".join(c.upper() if c.upper() in SCORES else BLANK for c in rack if c.strip())
    moves: List[Move] = []

    _generate_horizontal(letters, blanks, rack, "across", moves)
    t_letters = _transpose(letters)
    t_blanks = _transpose(blanks)
    _generate_horizontal(t_letters, t_blanks, rack, "down", moves)

    # Deduplicate physical plays (single-tile plays can appear in both orientations),
    # then attach the rack leave and sort.
    best: Dict[Tuple, Move] = {}
    for move in moves:
        k = move.key()
        if k not in best or move.score > best[k].score:
            best[k] = move

    result = list(best.values())
    for move in result:
        move.leave = _leave(rack, move.tiles)
        move.leave_value = leave_value(move.leave)
        move.equity = move.score + move.leave_value
    result.sort(key=lambda m: (-m.score, m.word))
    return result


def _leave(rack: str, tiles: List[PlacedTile]) -> str:
    remaining = Counter(rack)
    for tile in tiles:
        remaining[BLANK if tile.is_blank else tile.letter] -= 1
    leftover: List[str] = []
    for letter, count in remaining.items():
        leftover.extend([letter] * max(0, count))
    return "".join(sorted(leftover))
