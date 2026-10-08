"""Headless balance simulation: seeded bot runs through the real game rules.

    uv run python scripts/balance_sim.py --seeds 20 --minutes 60

Reports, per seed, minutes to reach the earnings goal, gold per minute and where
the gems came from, then medians across seeds. Use it before and after tuning
prices, drop rates or difficulty.
"""

import argparse
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.bot import simulate_run  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=10, help="number of seeds (1..N)")
    parser.add_argument("--minutes", type=float, default=60.0, help="game-time cap per run")
    parser.add_argument(
        "--bag",
        type=int,
        default=None,
        help="sell at this many items (default: when the bag is full)",
    )
    args = parser.parse_args()

    reports = [
        simulate_run(seed, max_minutes=args.minutes, bag_limit=args.bag)
        for seed in range(1, args.seeds + 1)
    ]
    print(f"{'seed':>5} {'win (min)':>10} {'died':>5} {'gold/min':>9}  gems by biome ($ raw)")
    for r in reports:
        win = f"{r.minutes_to_win:.1f}" if r.minutes_to_win is not None else "-"
        biomes = ", ".join(f"{b} {v}" for b, v in sorted(r.earnings_by_biome.items()))
        print(f"{r.seed:>5} {win:>10} {str(r.died):>5} {r.gold_per_minute:>9.0f}  {biomes}")

    wins = [r.minutes_to_win for r in reports if r.minutes_to_win is not None]
    print()
    print(f"won {len(wins)}/{len(reports)}, died {sum(r.died for r in reports)}")
    if wins:
        print(f"median minutes to win: {statistics.median(wins):.1f}")
    print(f"median gold/min: {statistics.median(r.gold_per_minute for r in reports):.0f}")


if __name__ == "__main__":
    main()
