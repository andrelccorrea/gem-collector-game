"""Rain: showers come and go with game time; caves stay dry.

Whether it rains is a stable hash of the seed and the current stretch of time (never the
gameplay RNG), so a run's weather is fixed. Rain greys the light (an overcast tint mixed
into the day/night tint) and is drawn as falling streaks; it changes nothing else.
"""

from game.decor import stable_random
from game.geography import biome_at

SHOWER_SECONDS = 90.0  # weather is decided per stretch of this many game seconds
RAIN_SHARE = 0.3  # share of stretches with rain
OVERCAST = (175, 185, 205)  # blue-grey
DROP_DENSITY = 0.03  # share of terminal cells with a drop
DROP_SPEED = 12.0  # cells per game second


def is_raining(state) -> bool:
    stretch = int(state.game_time // SHOWER_SECONDS)
    return stable_random(state.seed, stretch, 4242) < RAIN_SHARE


def rain_here(state) -> bool:
    """Raining where the player is (never underground)."""
    return is_raining(state) and biome_at(state.player_x, state.player_y) != "cave"


def render_rain(renderer, state, view) -> None:
    """Terminal rain: sparse ' drops falling over the world cells."""
    if not rain_here(state):
        return
    fall = int(state.game_time * DROP_SPEED)
    for sy in range(view.height):
        for sx in range(view.width):
            if stable_random(state.seed, view.x + sx, view.y + sy - fall) < DROP_DENSITY:
                _, colors = renderer.get_cell(sx, sy)
                background = colors[1] if colors else (0, 0, 0)
                renderer.set_cell(sx, sy, "'", ((150, 180, 235), background))
