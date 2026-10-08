"""The lantern: light that burns down outside town and sets the fog-of-war radius."""

from game.constants import FOG_RADIUS
from game.geography import biome_at, in_town
from game.objects.registry import LANTERN

# Below this share of fuel the HUD warns the player to head back.
LOW_FUEL_SHARE = 0.25


def lantern_capacity(state) -> float:
    return float(LANTERN["capacities"][state.lantern_level])


def fuel_share(state) -> float:
    return max(0.0, min(1.0, state.lantern_fuel / lantern_capacity(state)))


def light_radius(state) -> int:
    """Fog radius: full while the lantern is full, shrinking to the minimum when empty."""
    low = LANTERN["min_radius"]
    return low + round((FOG_RADIUS - low) * fuel_share(state))


def update_lantern(state, dt: float) -> None:
    """Refill in town; elsewhere burn fuel at the rate of the biome the player is in."""
    if in_town(state.player_x, state.player_y):
        state.lantern_fuel = lantern_capacity(state)
        return
    drain = LANTERN["drain"][biome_at(state.player_x, state.player_y)]
    state.lantern_fuel = max(0.0, state.lantern_fuel - drain * dt)
