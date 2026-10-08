"""Daily run: everyone gets the same world on the same day, with a time limit."""

from datetime import date

from game.simulation import new_run

# Game time for a daily run, in seconds.
DAILY_TIME_LIMIT = 15 * 60.0


def daily_seed(day: date) -> int:
    """Same seed for everyone on a given calendar day, e.g. 2026-10-08 -> 20261008."""
    return int(day.strftime("%Y%m%d"))


def start_daily(day: date):
    state = new_run(daily_seed(day))
    state.daily = day.isoformat()
    return state


def time_left(state) -> float:
    return max(0.0, DAILY_TIME_LIMIT - state.game_time)


def check_daily_end(state) -> None:
    if state.daily and state.game_time >= DAILY_TIME_LIMIT:
        state.active_scene = "daily_end"
