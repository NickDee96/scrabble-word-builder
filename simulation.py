"""Monte-Carlo simulation for best-play ranking (Phase 6.D).

Static equity (``score + leave``) already answers "which play is worth most *right
now*". Simulation answers the stronger question: **which play helps us win the game?**
For each of the top candidate plays we roll the game forward two plies —

    my play  ->  opponent's best static reply  ->  my best static reply

— sampling the *unseen* tile pool (opponent rack + bag) each time, and average the
resulting spread and win probability. A play that scores a little less but leaves a
rack that tends to score big next turn will win more rollouts, and rank higher.

This is the correctness-focused Python implementation described in
``best-play-engine-plan.md`` (Phase 6.D). It reuses :func:`board_engine.generate_moves`
for move generation and :func:`leaves.leave_value` for the horizon leave estimate, and
spends its iteration budget where it matters via a UCB-style racing/early-stop rule.
A compiled move generator can replace the hot inner loop later for more rollouts.
"""
from __future__ import annotations

import math
import random
import time
from collections import Counter
from dataclasses import dataclass
from statistics import fmean
from typing import Dict, List, Optional

from board_engine import (
    BLANK,
    BOARD_SIZE,
    TILE_DISTRIBUTION,
    Move,
    generate_moves,
)
from leaves import leave_value

RACK_SIZE = 7

# --- Win-probability model -------------------------------------------------
# We treat the eventual final margin as the simulated 2-ply spread plus zero-mean
# noise whose spread grows with how many tiles are still to be drawn: the more of the
# game that remains, the less a given lead settles the outcome. sigma(t) grows with the
# number of future "rounds" (tiles_left / RACK_SIZE). These constants are heuristic
# (not learned from self-play) but give a smooth, interpretable P(win); the plan
# describes replacing them with a learned (spread, tiles-left) -> P(win) table.
WIN_SIGMA_BASE = 45.0        # points of std-dev with an (almost) empty bag
WIN_SIGMA_PER_ROUND = 1.0    # weight on future rounds inside the sqrt

Grid = List[List[Optional[str]]]
BoolGrid = List[List[bool]]


@dataclass
class SimResult:
    """Simulation outcome for one candidate play."""

    move: Move
    rollouts: int
    equity: float       # mean simulated spread (points)
    win_pct: float      # mean win probability in [0, 1]
    std_err: float      # standard error of the mean spread


def win_probability(margin: float, tiles_left: int) -> float:
    """P(win) given a point ``margin`` with ``tiles_left`` tiles still unseen.

    Uses a normal model: final margin ~ N(margin, sigma(tiles_left)^2). A larger bag
    means a wider distribution and a P(win) closer to 0.5 for the same lead.
    """
    rounds = max(0, tiles_left) / RACK_SIZE
    sigma = WIN_SIGMA_BASE * math.sqrt(1.0 + WIN_SIGMA_PER_ROUND * rounds)
    if sigma <= 0.0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
    return 0.5 * (1.0 + math.erf(margin / (sigma * math.sqrt(2.0))))


def unseen_pool(letters: Grid, blanks: BoolGrid, rack: str) -> Counter:
    """Tiles neither on the board nor in our rack — the opponent's rack plus the bag.

    Board tiles played as blanks consume a blank from the pool (not the shown letter).
    Counts are clamped at zero to tolerate slightly inconsistent input.
    """
    pool = Counter(TILE_DISTRIBUTION)
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            ch = letters[r][c]
            if ch is None:
                continue
            pool[BLANK if blanks[r][c] else ch] -= 1
    for ch in rack:
        if ch in (BLANK, " "):
            pool[BLANK] -= 1
        elif ch.isalpha():
            pool[ch.upper()] -= 1
    return Counter({tile: n for tile, n in pool.items() if n > 0})


def _pool_list(pool: Counter) -> List[str]:
    tiles: List[str] = []
    for tile, n in pool.items():
        tiles.extend([tile] * n)
    return tiles


def _apply_move(letters: Grid, blanks: BoolGrid, move: Move):
    new_l = [row[:] for row in letters]
    new_b = [row[:] for row in blanks]
    for t in move.tiles:
        new_l[t.row][t.col] = t.letter
        new_b[t.row][t.col] = t.is_blank
    return new_l, new_b


def _best_static(letters: Grid, blanks: BoolGrid, rack: str) -> Optional[Move]:
    """The single highest-equity legal play for ``rack`` (or ``None`` if there is none)."""
    if not rack:
        return None
    moves = generate_moves(letters, blanks, rack)
    if not moves:
        return None
    return max(moves, key=lambda m: (m.equity, m.score))


def _rollout(
    board_l: Grid,
    board_b: BoolGrid,
    s0: float,
    residue: str,
    pool_list: List[str],
    score_margin: float,
    rng: random.Random,
) -> tuple:
    """One 2-ply rollout. Returns ``(spread, tiles_left)`` for the win-prob model.

    ``board_l/board_b`` already have our candidate play applied and ``s0`` is its score;
    ``residue`` is the rack we keep after it.
    """
    deck = pool_list[:]
    rng.shuffle(deck)
    opp_rack = "".join(deck[:RACK_SIZE])
    rest = deck[RACK_SIZE:]

    opp = _best_static(board_l, board_b, opp_rack)
    if opp is not None:
        s1 = opp.score
        opp_leave_v = opp.leave_value
        b2l, b2b = _apply_move(board_l, board_b, opp)
    else:
        s1 = 0.0
        opp_leave_v = leave_value(opp_rack)
        b2l, b2b = board_l, board_b

    need = max(0, RACK_SIZE - len(residue))
    my_draw = rest[:need]
    my_rack = residue + "".join(my_draw)
    tiles_left = len(rest) - len(my_draw)

    me = _best_static(b2l, b2b, my_rack)
    if me is not None:
        s2 = me.score
        my_leave_v = me.leave_value
    else:
        s2 = 0.0
        my_leave_v = leave_value(my_rack)

    spread = score_margin + (s0 + s2 + my_leave_v) - (s1 + opp_leave_v)
    return spread, tiles_left


def simulate(
    letters: Grid,
    blanks: BoolGrid,
    rack: str,
    *,
    max_candidates: int = 8,
    time_budget_ms: int = 5000,
    max_rollouts: int = 60,
    min_rollouts: int = 3,
    batch: int = 3,
    score_margin: float = 0.0,
    seed: Optional[int] = None,
) -> List[SimResult]:
    """Rank plays by simulated win probability.

    Takes the top ``max_candidates`` plays by static equity and rolls each forward two
    plies, sampling the unseen pool. Time-budgeted with a UCB-style racing rule that
    stops spending rollouts on candidates that cannot catch the leader. Returns results
    sorted by win probability (then simulated spread), each annotated with the number of
    rollouts run and the standard error so callers can show confidence.
    """
    rng = random.Random(seed)
    moves = generate_moves(letters, blanks, rack)
    if not moves:
        return []

    # Candidate set: best placement of each distinct word, top N by static equity.
    by_word: Dict[str, Move] = {}
    for m in sorted(moves, key=lambda m: (-m.equity, -m.score, m.word)):
        by_word.setdefault(m.word, m)
    candidates = list(by_word.values())[:max_candidates]

    pool_list = _pool_list(unseen_pool(letters, blanks, rack))

    # Pre-apply each candidate once (the board it leaves is fixed across its rollouts).
    boards = {id(c): _apply_move(letters, blanks, c) for c in candidates}
    spreads: Dict[int, List[float]] = {id(c): [] for c in candidates}
    winps: Dict[int, List[float]] = {id(c): [] for c in candidates}

    deadline = time.monotonic() + time_budget_ms / 1000.0
    active = list(candidates)

    def run_batch(c: Move, n: int) -> None:
        board_l, board_b = boards[id(c)]
        for _ in range(n):
            spread, tiles_left = _rollout(
                board_l, board_b, c.score, c.leave, pool_list, score_margin, rng
            )
            spreads[id(c)].append(spread)
            winps[id(c)].append(win_probability(spread, tiles_left))

    # Seed every candidate with a minimum number of rollouts.
    for c in active:
        run_batch(c, min_rollouts)
        if time.monotonic() >= deadline:
            break

    # Race the survivors: spend the rest of the budget on candidates that could still win.
    while time.monotonic() < deadline and len(active) > 1:
        if all(len(spreads[id(c)]) >= max_rollouts for c in active):
            break
        for c in active:
            if len(spreads[id(c)]) < max_rollouts:
                run_batch(c, batch)
            if time.monotonic() >= deadline:
                break
        active = _prune(active, spreads)

    results: List[SimResult] = []
    for c in candidates:
        sp = spreads[id(c)]
        if not sp:
            continue
        n = len(sp)
        mean_spread = fmean(sp)
        std_err = _std(sp) / math.sqrt(n) if n > 1 else 0.0
        results.append(
            SimResult(
                move=c,
                rollouts=n,
                equity=mean_spread,
                win_pct=fmean(winps[id(c)]),
                std_err=std_err,
            )
        )
    results.sort(key=lambda r: (-r.win_pct, -r.equity))
    return results


def _std(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = fmean(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


def _prune(active: List[Move], spreads: Dict[int, List[float]]) -> List[Move]:
    """Drop candidates whose spread upper bound is below the leader's lower bound (95%)."""
    stats = []
    for c in active:
        sp = spreads[id(c)]
        n = len(sp)
        mean = fmean(sp)
        se = _std(sp) / math.sqrt(n) if n > 1 else float("inf")
        stats.append((c, mean, se))
    leader = max(stats, key=lambda s: s[1])
    lead_lb = leader[1] - 2.0 * leader[2]
    survivors = [c for (c, mean, se) in stats if mean + 2.0 * se >= lead_lb]
    if leader[0] not in survivors:
        survivors.append(leader[0])
    return survivors
