"""Tests for the Monte-Carlo best-play simulation (simulation.py, Phase 6.D).

The move-level tests use tiny rollout budgets so the suite stays fast; they assert the
engine's *invariants* (bounded win %, correct sorting, unseen-pool accounting,
determinism under a fixed seed) rather than exact simulated values.
"""
from board_engine import TILE_DISTRIBUTION
from simulation import simulate, unseen_pool, win_probability


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


# --------------------------------------------------------------------------- #
# Unseen pool
# --------------------------------------------------------------------------- #
def test_unseen_pool_excludes_board_and_rack():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "STARE")  # S T A R E on the board
    pool = unseen_pool(letters, blanks, "AET")  # keep A E T in hand

    # Full bag minus the five board tiles minus the three rack tiles.
    assert pool["S"] == TILE_DISTRIBUTION["S"] - 1
    assert pool["A"] == TILE_DISTRIBUTION["A"] - 1 - 1  # one on board, one in rack
    assert pool["E"] == TILE_DISTRIBUTION["E"] - 1 - 1
    assert pool["T"] == TILE_DISTRIBUTION["T"] - 1 - 1
    assert sum(pool.values()) == 100 - 5 - 3


def test_unseen_pool_counts_board_blank_as_blank():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "STARE", blank_positions=(0,))  # S is a blank tile
    pool = unseen_pool(letters, blanks, "")

    # The blank S consumes a blank from the pool, not an S.
    assert pool["S"] == TILE_DISTRIBUTION["S"]
    assert pool["?"] == TILE_DISTRIBUTION["?"] - 1


def test_unseen_pool_never_negative():
    letters, blanks = _empty()
    # More S's claimed than exist should clamp at zero, not go negative.
    pool = unseen_pool(letters, blanks, "SSSSS")
    assert pool["S"] == 0
    assert all(v >= 0 for v in pool.values())


# --------------------------------------------------------------------------- #
# Win-probability model
# --------------------------------------------------------------------------- #
def test_win_probability_bounds_and_symmetry():
    assert 0.0 <= win_probability(-200, 40) <= 1.0
    assert win_probability(0, 40) == 0.5
    assert win_probability(60, 20) > 0.5 > win_probability(-60, 20)
    # Symmetric around zero.
    assert abs(win_probability(30, 10) + win_probability(-30, 10) - 1.0) < 1e-9


def test_win_probability_more_tiles_left_is_less_certain():
    # The same lead is less decisive when more tiles remain to be drawn.
    near_end = win_probability(40, 2)
    early = win_probability(40, 80)
    assert 0.5 < early < near_end


# --------------------------------------------------------------------------- #
# simulate()
# --------------------------------------------------------------------------- #
def test_simulate_no_legal_move_returns_empty():
    letters, blanks = _empty()
    letters[7][7] = "Q"  # lone Q: no legal play with a V
    assert simulate(letters, blanks, "V", time_budget_ms=500, seed=1) == []


def test_simulate_returns_bounded_ranked_results():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "STARE")
    results = simulate(
        letters,
        blanks,
        "AT",
        max_candidates=3,
        min_rollouts=1,
        max_rollouts=2,
        time_budget_ms=4000,
        seed=7,
    )
    assert results, "expected at least one simulated candidate"
    assert len(results) <= 3
    for r in results:
        assert 0.0 <= r.win_pct <= 1.0
        assert r.rollouts >= 1
        assert r.std_err >= 0.0
    # Results are ordered by win probability (then simulated spread).
    keys = [(-r.win_pct, -r.equity) for r in results]
    assert keys == sorted(keys)


def test_simulate_is_deterministic_with_seed():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "STARE")
    kwargs = dict(
        max_candidates=3,
        min_rollouts=2,
        max_rollouts=2,  # == min_rollouts -> fixed rollout count, no time-based variance
        time_budget_ms=60000,
        seed=123,
    )
    first = simulate(letters, blanks, "AT", **kwargs)
    second = simulate(letters, blanks, "AT", **kwargs)
    assert [(r.move.word, round(r.win_pct, 6), round(r.equity, 6)) for r in first] == [
        (r.move.word, round(r.win_pct, 6), round(r.equity, 6)) for r in second
    ]


def test_simulate_score_margin_shifts_win_probability():
    letters, blanks = _empty()
    _place(letters, blanks, 7, 7, "STARE")
    common = dict(max_candidates=2, min_rollouts=2, max_rollouts=2, time_budget_ms=60000, seed=5)
    behind = simulate(letters, blanks, "AT", score_margin=-100, **common)
    ahead = simulate(letters, blanks, "AT", score_margin=100, **common)
    # A big current lead should not lower our win estimate versus being far behind.
    assert max(r.win_pct for r in ahead) >= max(r.win_pct for r in behind)
