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

import atexit
import math
import os
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
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


# --- Parallel execution (optional multiprocessing) -------------------------
# Rollouts are independent, so they parallelize cleanly across CPU cores. A persistent
# process pool is built once (each worker warms the dictionary trie in its initializer)
# and reused across requests. Set SIM_WORKERS=1 to disable; any pool failure falls back
# to the sequential path so behaviour never breaks.
_POOL: "Optional[ProcessPoolExecutor]" = None


def _worker_init() -> None:  # pragma: no cover - runs in a worker subprocess
    try:
        from board_engine import _trie

        _trie()
    except Exception:
        pass


def _resolve_workers(workers: Optional[int]) -> int:
    # Each worker holds its own dictionary trie (~0.5 GB), so the default is capped for
    # memory; SIM_WORKERS can raise it up to the hard cap below.
    default = min(os.cpu_count() or 1, 4)
    if workers is None:
        env = os.getenv("SIM_WORKERS")
        if env:
            try:
                workers = int(env)
            except ValueError:
                workers = default
        else:
            workers = default
    try:
        workers = int(workers)
    except (TypeError, ValueError):
        workers = 1
    return max(1, min(workers, os.cpu_count() or 1, 8))


def _noop_warm() -> bool:  # pragma: no cover - runs in a worker subprocess
    from board_engine import _trie

    _trie()
    return True


def _get_pool(n_workers: int) -> "Optional[ProcessPoolExecutor]":
    global _POOL
    if n_workers <= 1:
        return None
    if _POOL is None:
        try:
            _POOL = ProcessPoolExecutor(max_workers=n_workers, initializer=_worker_init)
            # Eagerly spawn + warm every worker (each builds its trie) so the first
            # analysis isn't charged for the ~seconds of warmup inside its time budget.
            for fut in [_POOL.submit(_noop_warm) for _ in range(n_workers)]:
                fut.result()
        except Exception:
            _POOL = None
    return _POOL


@atexit.register
def _shutdown_pool() -> None:  # pragma: no cover
    global _POOL
    if _POOL is not None:
        try:
            _POOL.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        _POOL = None


def _rollout_batch_worker(payload):  # pragma: no cover - runs in a worker subprocess
    board_l, board_b, s0, residue, pool_list, score_margin, seeds = payload
    out = []
    for s in seeds:
        out.append(
            _rollout(board_l, board_b, s0, residue, pool_list, score_margin, random.Random(s))
        )
    return out


def _collect(candidates, spreads, winps) -> List[SimResult]:
    results: List[SimResult] = []
    for c in candidates:
        sp = spreads[id(c)]
        if not sp:
            continue
        n = len(sp)
        std_err = _std(sp) / math.sqrt(n) if n > 1 else 0.0
        results.append(
            SimResult(
                move=c, rollouts=n, equity=fmean(sp), win_pct=fmean(winps[id(c)]), std_err=std_err
            )
        )
    results.sort(key=lambda r: (-r.win_pct, -r.equity))
    return results


def _simulate_parallel(
    candidates,
    boards,
    pool_list,
    *,
    time_budget_ms,
    max_rollouts,
    min_rollouts,
    batch,
    score_margin,
    seed,
    rollouts,
    n_workers,
) -> "Optional[List[SimResult]]":
    """Run rollouts across the process pool. Returns ``None`` if the pool is unavailable.

    ``rollouts`` set -> fixed count per candidate (reproducible with a seed); otherwise a
    time-budgeted top-two Thompson allocation across the candidates.
    """
    pool = _get_pool(n_workers)
    if pool is None:
        return None
    spreads: Dict[int, List[float]] = {id(c): [] for c in candidates}
    winps: Dict[int, List[float]] = {id(c): [] for c in candidates}
    master = random.Random(seed if seed is not None else random.randrange(1 << 30))
    deadline = time.monotonic() + time_budget_ms / 1000.0

    def run(alloc) -> None:
        futures = []
        for c, k in alloc:
            if k <= 0:
                continue
            board_l, board_b = boards[id(c)]
            seeds = [master.randrange(1 << 31) for _ in range(k)]
            payload = (board_l, board_b, c.score, c.leave, pool_list, score_margin, seeds)
            futures.append((c, pool.submit(_rollout_batch_worker, payload)))
        for c, fut in futures:
            for spread, tiles_left in fut.result():
                spreads[id(c)].append(spread)
                winps[id(c)].append(win_probability(spread, tiles_left))

    try:
        if rollouts is not None:  # reproducible fixed count -> equal allocation
            while any(len(spreads[id(c)]) < rollouts for c in candidates):
                run([(c, min(batch, rollouts - len(spreads[id(c)]))) for c in candidates])
            return _collect(candidates, spreads, winps)

        run([(c, min_rollouts) for c in candidates])  # seed every arm's posterior
        while time.monotonic() < deadline:
            active = [c for c in candidates if len(spreads[id(c)]) < max_rollouts]
            if not active:
                break
            counts = _bandit_counts(active, winps, batch * n_workers, master)
            alloc = [
                (c, min(counts.get(id(c), 0), max_rollouts - len(spreads[id(c)]))) for c in active
            ]
            if not any(k > 0 for _, k in alloc):
                break
            run(alloc)
    except Exception:
        return None
    return _collect(candidates, spreads, winps)


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
    workers: Optional[int] = None,
    rollouts: Optional[int] = None,
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
    by_word: Dict[str, Move] = {}
    for m in sorted(moves, key=lambda m: (-m.equity, -m.score, m.word)):
        by_word.setdefault(m.word, m)
    candidates = list(by_word.values())[:max_candidates]

    pool_list = _pool_list(unseen_pool(letters, blanks, rack))

    # Pre-apply each candidate once (the board it leaves is fixed across its rollouts).
    boards = {id(c): _apply_move(letters, blanks, c) for c in candidates}

    # Prefer the process pool (all cores) when enabled; fall back to sequential on failure.
    n_workers = _resolve_workers(workers)
    if n_workers > 1:
        parallel = _simulate_parallel(
            candidates,
            boards,
            pool_list,
            time_budget_ms=time_budget_ms,
            max_rollouts=max_rollouts,
            batch=batch,
            score_margin=score_margin,
            seed=seed,
            rollouts=rollouts,
            n_workers=n_workers,
            min_rollouts=min_rollouts,
        )
        if parallel is not None:
            return parallel

    spreads: Dict[int, List[float]] = {id(c): [] for c in candidates}
    winps: Dict[int, List[float]] = {id(c): [] for c in candidates}

    def run_batch(c: Move, n: int) -> None:
        board_l, board_b = boards[id(c)]
        for _ in range(n):
            spread, tiles_left = _rollout(
                board_l, board_b, c.score, c.leave, pool_list, score_margin, rng
            )
            spreads[id(c)].append(spread)
            winps[id(c)].append(win_probability(spread, tiles_left))

    if rollouts:  # fixed count -> reproducible with a seed (no racing/early stop)
        for c in candidates:
            run_batch(c, rollouts)
        return _collect(candidates, spreads, winps)

    deadline = time.monotonic() + time_budget_ms / 1000.0
    for c in candidates:  # seed every candidate so its posterior is initialised
        run_batch(c, min_rollouts)
        if time.monotonic() >= deadline:
            break
    # Top-two Thompson sampling: spend the remaining budget on the leader and its challenger.
    while time.monotonic() < deadline:
        active = [c for c in candidates if len(spreads[id(c)]) < max_rollouts]
        if not active:
            break
        counts = _bandit_counts(active, winps, batch, rng)
        spent = False
        for c in active:
            k = min(counts.get(id(c), 0), max_rollouts - len(spreads[id(c)]))
            if k > 0:
                run_batch(c, k)
                spent = True
            if time.monotonic() >= deadline:
                break
        if not spent:
            break
    return _collect(candidates, spreads, winps)


def _std(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = fmean(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))


# --- Top-two Thompson sampling allocation (best-arm identification) ---------
# Rollouts are scarce, so instead of spreading them evenly we model each candidate's win%
# as a Normal posterior over its mean and, each round, sample a "leader" plus (half the
# time) its closest "challenger", spending the next rollouts on those two. This is Russo's
# top-two Thompson sampling for best-arm identification: far more discriminating power per
# rollout than uniform sampling or confidence-bound racing.
_TTTS_BETA = 0.5            # P(sample the leader) vs its challenger each draw
_BANDIT_PRIOR_SIGMA = 0.35  # posterior std for an arm with a single sample (win% in [0, 1])
_BANDIT_MIN_SIGMA = 0.01    # floor so a confident arm can still be revisited


def _posterior_stats(samples: List[float]):
    """Mean and posterior std of an arm's mean win% (wide when barely sampled)."""
    n = len(samples)
    if n == 0:
        return 0.0, _BANDIT_PRIOR_SIGMA * 4
    mean = fmean(samples)
    if n < 2:
        return mean, _BANDIT_PRIOR_SIGMA
    return mean, max(_std(samples) / math.sqrt(n), _BANDIT_MIN_SIGMA)


def _ttts_pick(stats, rng: random.Random) -> int:
    """Index of the next arm to sample, via top-two Thompson sampling."""
    draws = [rng.gauss(mean, sigma) for mean, sigma in stats]
    leader = max(range(len(stats)), key=lambda i: draws[i])
    if len(stats) == 1 or rng.random() < _TTTS_BETA:
        return leader
    # Challenger: the best arm other than the leader in a fresh posterior sample.
    cdraws = [rng.gauss(mean, sigma) for mean, sigma in stats]
    cdraws[leader] = float("-inf")
    return max(range(len(stats)), key=lambda i: cdraws[i])


def _bandit_counts(active, winps, slots: int, rng: random.Random) -> Dict[int, int]:
    """Split ``slots`` upcoming rollouts across ``active`` arms by top-two Thompson."""
    stats = [_posterior_stats(winps[id(c)]) for c in active]
    counts: Dict[int, int] = {}
    for _ in range(max(1, slots)):
        cid = id(active[_ttts_pick(stats, rng)])
        counts[cid] = counts.get(cid, 0) + 1
    return counts
