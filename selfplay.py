"""Two-agent self-play — watch an equity player face a Monte-Carlo player.

A light, **stateless** turn engine behind the ``/api/selfplay`` endpoints. The client holds
the whole game state (board text, both racks, the remaining bag, scores) and asks the server
to play a single turn at a time, so the UI can animate the game move by move.

Each side is an *agent*:

* ``"equity"`` — plays the highest static-equity move (score + leave), the Quackle-style
  greedy baseline.
* ``"simulation"`` — plays the move with the best simulated **win %** (see :mod:`simulation`).

The board is exchanged as 15 lines of text (uppercase = tile, lowercase = blank tile,
``.`` = empty) to keep payloads tiny — the same format the board analyzer copy/paste uses.
"""
from __future__ import annotations

import copy
import random
from collections import Counter
from typing import Dict, List, Optional, Tuple

from board_engine import BLANK, BOARD_SIZE, TILE_DISTRIBUTION, Move, generate_moves
from scrabble_engine import SCORES
from simulation import simulate

RACK_SIZE = 7
_PASS_LIMIT = 6  # game ends after this many consecutive scoreless turns (2 players x 3)

Grid = List[List[Optional[str]]]
BoolGrid = List[List[bool]]


# --- Board text <-> grids --------------------------------------------------
def parse_board(text: str) -> Tuple[Grid, BoolGrid]:
    letters: Grid = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    blanks: BoolGrid = [[False] * BOARD_SIZE for _ in range(BOARD_SIZE)]
    for r, line in enumerate(text.split("\n")[:BOARD_SIZE]):
        for c, ch in enumerate(line[:BOARD_SIZE]):
            if "A" <= ch <= "Z":
                letters[r][c] = ch
            elif "a" <= ch <= "z":
                letters[r][c] = ch.upper()
                blanks[r][c] = True
    return letters, blanks


def board_to_text(letters: Grid, blanks: BoolGrid) -> str:
    rows = []
    for r in range(BOARD_SIZE):
        cells = []
        for c in range(BOARD_SIZE):
            ch = letters[r][c]
            if ch is None:
                cells.append(".")
            elif blanks[r][c]:
                cells.append(ch.lower())
            else:
                cells.append(ch.upper())
        rows.append("".join(cells))
    return "\n".join(rows)


def _rack_value(rack: str) -> int:
    """Face value of tiles left on a rack (blanks are worth 0)."""
    return sum(SCORES.get(c, 0) for c in rack if c != BLANK)


def _counter_to_rack(counter: Counter) -> str:
    return "".join(tile * max(0, n) for tile, n in counter.items())


# --- Game lifecycle --------------------------------------------------------
def new_game(seed: Optional[int] = None) -> dict:
    """Deal a fresh game: empty board, two random racks, the rest in the bag."""
    rng = random.Random(seed)
    bag: List[str] = []
    for tile, n in TILE_DISTRIBUTION.items():
        bag.extend([tile] * n)
    rng.shuffle(bag)
    rack_a = "".join(bag[:RACK_SIZE])
    rack_b = "".join(bag[RACK_SIZE : 2 * RACK_SIZE])
    rest = bag[2 * RACK_SIZE :]
    return {
        "board": "\n".join("." * BOARD_SIZE for _ in range(BOARD_SIZE)),
        "racks": {"A": rack_a, "B": rack_b},
        "bag": "".join(rest),
        "scores": {"A": 0, "B": 0},
        "turn": "A",
        "passes": 0,
        "moveNumber": 0,
        "over": False,
        "winner": None,
    }


def _finish(state: dict) -> None:
    state["over"] = True
    a, b = state["scores"]["A"], state["scores"]["B"]
    state["winner"] = "A" if a > b else "B" if b > a else "tie"


def _best_move(letters: Grid, blanks: BoolGrid, rack: str, agent: str,
               time_budget_ms: int, max_candidates: int, seed: Optional[int]):
    """Return ``(move, extra)`` for the agent, where ``extra`` carries win% / iterations."""
    if not rack.strip():
        return None, {}
    if agent == "simulation":
        results = simulate(
            letters, blanks, rack,
            max_candidates=max_candidates, time_budget_ms=time_budget_ms, seed=seed,
        )
        if not results:
            return None, {}
        top = results[0]
        return top.move, {"winPct": round(top.win_pct, 3), "iterations": top.rollouts}
    moves = generate_moves(letters, blanks, rack)
    if not moves:
        return None, {}
    return max(moves, key=lambda m: (m.equity, m.score)), {}


def play_turn(
    state: dict,
    agent: str,
    *,
    time_budget_ms: int = 2000,
    max_candidates: int = 8,
    seed: Optional[int] = None,
) -> Tuple[dict, dict]:
    """Play one turn for the side to move using ``agent`` and return ``(new_state, move)``."""
    state = copy.deepcopy(state)
    turn = state["turn"]
    move: dict = {
        "type": "pass", "player": turn, "agent": agent, "word": "", "row": -1, "col": -1,
        "direction": "", "score": 0, "leave": "", "equity": None, "winPct": None,
        "iterations": None, "tiles": [],
    }
    if state.get("over"):
        move["type"] = "none"
        return state, move

    opp = "B" if turn == "A" else "A"
    rack = state["racks"][turn]
    bag = list(state["bag"])
    rng = random.Random(seed)
    letters, blanks = parse_board(state["board"])

    best, extra = _best_move(letters, blanks, rack, agent, time_budget_ms, max_candidates, seed)

    if best is not None:
        for t in best.tiles:
            letters[t.row][t.col] = t.letter
            blanks[t.row][t.col] = t.is_blank
        counter = Counter(rack)
        for t in best.tiles:
            counter[BLANK if t.is_blank else t.letter] -= 1
        new_rack = _counter_to_rack(counter)
        need = max(0, RACK_SIZE - len(new_rack))
        rng.shuffle(bag)
        drawn, bag = bag[:need], bag[need:]
        new_rack += "".join(drawn)

        state["racks"][turn] = new_rack
        state["scores"][turn] += best.score
        state["bag"] = "".join(bag)
        state["board"] = board_to_text(letters, blanks)
        state["passes"] = 0
        move.update(
            type="play", word=best.word, row=best.row, col=best.col,
            direction=best.direction, score=best.score, leave=best.leave,
            equity=round(best.equity, 1),
            tiles=[
                {"row": t.row, "col": t.col, "letter": t.letter, "blank": t.is_blank}
                for t in best.tiles
            ],
        )
        move.update(extra)
        if not new_rack and not bag:  # played out with an empty bag -> game over
            opp_val = _rack_value(state["racks"][opp])
            state["scores"][turn] += opp_val
            state["scores"][opp] -= opp_val
            _finish(state)
    else:
        # No legal move: exchange the rack if the bag can support it, otherwise pass.
        if rack.strip() and len(bag) >= RACK_SIZE:
            bag.extend(rack)
            rng.shuffle(bag)
            n = len(rack)
            state["racks"][turn] = "".join(bag[:n])
            state["bag"] = "".join(bag[n:])
            move["type"] = "exchange"
        else:
            move["type"] = "pass"
        state["passes"] = state.get("passes", 0) + 1
        if state["passes"] >= _PASS_LIMIT:
            for p in ("A", "B"):
                state["scores"][p] -= _rack_value(state["racks"][p])
            _finish(state)

    state["moveNumber"] = state.get("moveNumber", 0) + 1
    if not state["over"]:
        state["turn"] = opp
    return state, move
