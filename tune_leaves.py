"""Offline tuner for the leave-value weights in :mod:`leaves` — the license-clean static
evaluator used by the equity agent and inside every Monte-Carlo rollout.

**Objective.** Maximize the average point margin of the *equity* agent (using the candidate
leave weights) against the fixed *score* agent (highest raw score, leave-independent) over
a batch of self-play games. Better leaves => the equity player keeps stronger racks =>
larger margin. Games are seeded and reused across trials (common random numbers), so the
objective is low-noise and isolates the effect of the weights.

**Optimizer.** Uses Ax (Bayesian optimization, powered by BoTorch) when installed, else
falls back to random search so the harness runs with no heavy dependency. Install the
optimizer with::

    pip install ax-platform

Run::

    python tune_leaves.py --games 24 --trials 25          # Ax if available, else random
    python tune_leaves.py --games 12 --trials 10 --random # force random search

This only writes results to stdout; it never edits leaves.py. Copy the printed weights
into leaves.py (or leaves.apply_params) once you're happy with them.
"""
from __future__ import annotations

import argparse
import random
from typing import Dict, Optional, Tuple

import leaves
from selfplay import play_game

# Parameter search space: name -> (low, high). Current shipped defaults in the comments.
PARAM_SPACE: Dict[str, Tuple[float, float]] = {
    "blank": (18.0, 32.0),                # 25
    "s": (4.0, 12.0),                     # 8
    "e": (1.0, 7.0),                      # 4
    "duplicate_penalty": (0.0, 5.0),      # 2
    "all_vowel_penalty": (0.0, 10.0),     # 5
    "all_consonant_penalty": (0.0, 8.0),  # 3
    "q_without_u_penalty": (0.0, 15.0),   # 8
}
METRIC = "win_margin"
_BASE_SEED = 1000


def evaluate(params: Dict[str, float], games: int = 24) -> float:
    """Mean (equity - score) point margin over ``games`` seeded self-play games."""
    leaves.apply_params(params)  # {} restores defaults, so this is idempotent per call
    total = 0
    for i in range(games):
        first = "A" if i % 2 == 0 else "B"  # alternate the opener for fairness
        result = play_game("equity", "score", first=first, seed=_BASE_SEED + i)
        total += result["scores"]["A"] - result["scores"]["B"]  # A = equity, B = score
    return total / games


def _random_search(games: int, trials: int) -> Tuple[Dict[str, float], float]:
    rng = random.Random(0)
    best_params: Optional[Dict[str, float]] = None
    best_val = float("-inf")
    for t in range(trials):
        params = {name: rng.uniform(lo, hi) for name, (lo, hi) in PARAM_SPACE.items()}
        val = evaluate(params, games)
        if val > best_val:
            best_val, best_params = val, params
        print(f"[random {t + 1:>3}/{trials}] margin={val:+7.1f}  best={best_val:+7.1f}")
    return best_params or {}, best_val


def _ax_search(games: int, trials: int) -> Tuple[Dict[str, float], float]:
    from ax.api.client import Client
    from ax.api.configs import RangeParameterConfig

    client = Client()
    client.configure_experiment(
        parameters=[
            RangeParameterConfig(name=name, parameter_type="float", bounds=bounds)
            for name, bounds in PARAM_SPACE.items()
        ]
    )
    client.configure_optimization(objective=METRIC)  # maximize

    best_params: Optional[Dict[str, float]] = None
    best_val = float("-inf")
    for t in range(trials):
        for index, params in client.get_next_trials(max_trials=1).items():
            val = evaluate(dict(params), games)
            client.complete_trial(trial_index=index, raw_data={METRIC: val})
            if val > best_val:
                best_val, best_params = val, dict(params)
            print(f"[ax {t + 1:>3}/{trials}] margin={val:+7.1f}  best={best_val:+7.1f}")
    return best_params or {}, best_val


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--games", type=int, default=24, help="self-play games per trial")
    ap.add_argument("--trials", type=int, default=25, help="parameter settings to try")
    ap.add_argument("--random", action="store_true", help="force random search (skip Ax)")
    args = ap.parse_args()

    baseline = evaluate({}, args.games)  # current shipped leaves
    print(f"baseline (current leaves) margin vs Score = {baseline:+.1f} over {args.games} games\n")

    method = "random"
    if not args.random:
        try:
            best_params, best_val = _ax_search(args.games, args.trials)
            method = "ax"
        except ImportError:
            print("ax-platform not installed -> random search "
                  "(`pip install ax-platform` for Bayesian optimization).\n")
            best_params, best_val = _random_search(args.games, args.trials)
    else:
        best_params, best_val = _random_search(args.games, args.trials)

    # Re-evaluate the winner to report a clean number, then restore defaults.
    final = evaluate(best_params, args.games)
    leaves.apply_params({})
    print(f"\n=== best weights ({method}): margin vs Score = {final:+.1f} "
          f"(baseline {baseline:+.1f}, delta {final - baseline:+.1f}) ===")
    for name in PARAM_SPACE:
        print(f"  {name:>22}: {best_params.get(name, float('nan')):.2f}")


if __name__ == "__main__":
    main()
