"""A scripted player for headless balance simulations.

The bot plays through the real simulation (``step_game``) with the same inputs a
person would press, and uses the real shop functions when standing in town, so its
results reflect the actual game rules. It is deliberately simple and greedy:
dig the nearest workable spot, fight what is adjacent, go home to sell when the bag
is heavy or HP is low, and spend gold on the best tool it can afford.
"""

from collections import deque
from dataclasses import dataclass, field

from game.constants import (
    MAP_HEIGHT,
    MAP_WIDTH,
    SHOP_X,
    SHOP_Y,
    TYPE_LAKE,
    TYPE_STREAM,
    WIN_LIFETIME_EARNINGS,
)
from game.enemies import find_path_bfs
from game.gems import bag_capacity, bag_count, get_gem_raw_value
from game.geography import biome_at
from game.input import Action, InputState
from game.loop import STEP
from game.objects.registry import TOOL_CATALOG
from game.simulation import new_run, step_game

_MOVES = {
    (-1, 0): Action.MOVE_LEFT,
    (1, 0): Action.MOVE_RIGHT,
    (0, -1): Action.MOVE_UP,
    (0, 1): Action.MOVE_DOWN,
}
_WORKABLE_EXTRA = {TYPE_STREAM, TYPE_LAKE}
_PURCHASES = {"buy_tool", "upgrade_tool", "upgrade_bag"}


@dataclass
class RunReport:
    seed: int
    minutes_to_win: float | None
    minutes_played: float
    lifetime_earnings: int
    died: bool
    earnings_by_biome: dict = field(default_factory=dict)

    @property
    def gold_per_minute(self) -> float:
        return self.lifetime_earnings / max(self.minutes_played, 1e-9)


class Bot:
    def __init__(self, state, bag_limit: int = 12, retreat_hp: float = 0.4):
        self.state = state
        self.bag_limit = bag_limit
        self.retreat_hp = retreat_hp
        self.path: list = []
        self.goal = None
        self.unreachable: set = set()
        self._idle_steps = 0  # wait before searching again after finding nothing
        self.earnings_by_biome: dict = {}
        self._known_gems = dict(state.inventory["gems"])

    # ── Decisions ────────────────────────────────────────────────────────────

    def next_input(self) -> InputState:
        s = self.state
        self._credit_new_gems()

        adjacent = [e for e in s.enemies if max(abs(e.x - s.player_x), abs(e.y - s.player_y)) <= 1]
        if adjacent:
            return _press(Action.ATTACK)

        if self._should_go_home():
            if (s.player_x, s.player_y) == (SHOP_X, SHOP_Y):
                self._trade()
                self.goal = None
                return InputState()
            return self._walk_to((SHOP_X, SHOP_Y))

        if self.goal is None or not self._is_workable(self.goal):
            if self._idle_steps > 0:
                self._idle_steps -= 1
                return InputState()
            # Look nearby first, then across the whole reachable map.
            self.goal = self._nearest_workable() or self._nearest_workable(limit=None)
            self.path = []
            if self.goal is None:
                self._idle_steps = 300
                return InputState()
        if (s.player_x, s.player_y) == self.goal:
            self._equip_for(self.goal)
            self.goal = None
            return _press(Action.USE)
        return self._walk_to(self.goal)

    def _should_go_home(self) -> bool:
        s = self.state
        full = bag_count(s) >= min(self.bag_limit, bag_capacity(s))
        low_hp = s.player_hp < s.player_max_hp * self.retreat_hp
        healing = low_hp and (s.player_x, s.player_y) == (SHOP_X, SHOP_Y)
        return full or low_hp or healing

    # ── World queries ─────────────────────────────────────────────────────────

    def _compatible_types(self) -> set:
        types = set()
        for tool in self.state.inventory["tools"]:
            types |= set(TOOL_CATALOG[tool].compatible_types)
        return types

    def _is_workable(self, pos) -> bool:
        s = self.state
        meta = s.world_tiles.meta.get(pos)
        if meta is None or meta.get("depleted") or pos in self.unreachable:
            return False
        compatible = self._compatible_types()
        if pos in s.world_gems:
            return meta["type"] in compatible
        mineable = meta.get("interactable") and meta["type"].startswith("mineable_")
        return (mineable or meta["type"] in _WORKABLE_EXTRA) and meta["type"] in compatible

    def _nearest_workable(self, limit: int | None = 4000):
        """Breadth-first search over walkable tiles for the closest workable spot."""
        s = self.state
        start = (s.player_x, s.player_y)
        seen, queue = {start}, deque([start])
        while queue and (limit is None or len(seen) < limit):
            pos = queue.popleft()
            if pos != start and self._is_workable(pos):
                return pos
            x, y = pos
            for nxt in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nxt in seen or not (0 <= nxt[0] < MAP_WIDTH and 0 <= nxt[1] < MAP_HEIGHT):
                    continue
                if s.world_tiles.meta.get(nxt, {}).get("walkable"):
                    seen.add(nxt)
                    queue.append(nxt)
        return None

    # ── Actions ──────────────────────────────────────────────────────────────

    def _walk_to(self, target) -> InputState:
        s = self.state
        here = (s.player_x, s.player_y)
        if not self.path or self.path[-1] != target or self.path[0] == here:
            self.path = find_path_bfs(s.world_tiles, *here, *target, max_steps=400)
            if not self.path or self.path[-1] != target:
                # Too far or cut off: give up on this spot instead of searching again.
                self.unreachable.add(target)
                self.goal = None
                self.path = []
                return InputState()
        step = self.path[0]
        if abs(step[0] - here[0]) + abs(step[1] - here[1]) != 1:
            self.path = []
            return InputState()
        move = _MOVES[(step[0] - here[0], step[1] - here[1])]
        # Each press is one step once the move cooldown allows it; the path advances
        # only when the player actually arrived on the next tile.
        self._pending_step = step
        return InputState(held=frozenset({move}))

    def after_step(self) -> None:
        s = self.state
        if self.path and (s.player_x, s.player_y) == self.path[0]:
            self.path.pop(0)

    def _equip_for(self, pos) -> None:
        s = self.state
        kind = s.world_tiles.meta[pos]["type"]
        for tool in s.inventory["tools"]:
            if kind in TOOL_CATALOG[tool].compatible_types:
                s.equipped_tool = tool
                return

    def _credit_new_gems(self) -> None:
        """Attribute each newly found gem's raw value to the biome it came from."""
        s = self.state
        biome = biome_at(s.player_x, s.player_y)
        for gem, count in s.inventory["gems"].items():
            if gem.endswith("_polished"):
                continue
            new = count - self._known_gems.get(gem, 0)
            if new > 0:
                value = get_gem_raw_value(gem) * new
                self.earnings_by_biome[biome] = self.earnings_by_biome.get(biome, 0) + value
        self._known_gems = dict(s.inventory["gems"])

    def _trade(self) -> None:
        """Sell everything, then buy the best tool or upgrade that is affordable."""
        from game.scenes.shop import _build_shop_items, update_shop

        s = self.state
        confirm = _press(Action.CONFIRM)

        def choose(tab, action, key=None):
            s.active_scene, s.shop_tab = "shop", tab
            for i, item in enumerate(_build_shop_items(s)):
                if item["action"] == action and (key is None or item["key"] == key):
                    s.shop_cursor = i
                    update_shop(confirm, s)
                    return True
            return False

        for tab, action in ((2, "sell_all_gems"), (3, "sell_all_loot")):
            choose(tab, action)
            if s.active_scene == "win":
                return
        for _ in range(10):
            # Cheapest purchase the shop currently offers (enabled = affordable and unlocked).
            offers = []
            for tab in (0, 1):
                s.shop_tab = tab
                for i, item in enumerate(_build_shop_items(s)):
                    if item["enabled"] and item["action"] in _PURCHASES:
                        offers.append((item["cost"], tab, i))
            if not offers:
                break
            _cost, s.shop_tab, s.shop_cursor = min(offers)
            update_shop(confirm, s)
        s.active_scene = "game"
        self._known_gems = dict(s.inventory["gems"])


def _press(action) -> InputState:
    return InputState(pressed=frozenset({action}))


def simulate_run(seed: int, max_minutes: float = 60.0, **bot_options) -> RunReport:
    """Play one seeded run with the bot until it wins, dies or runs out of time."""
    state = new_run(seed)
    bot = Bot(state, **bot_options)
    max_steps = int(max_minutes * 60 / STEP)
    won_at = None
    for _ in range(max_steps):
        step_game(bot.next_input(), state, STEP)
        bot.after_step()
        if state.active_scene == "win":
            won_at = state.game_time / 60
            break
        if state.active_scene == "death":
            break
        state.active_scene = "game"  # the bot never opens menus
    return RunReport(
        seed=seed,
        minutes_to_win=won_at,
        minutes_played=state.game_time / 60,
        lifetime_earnings=state.lifetime_earnings,
        died=state.active_scene == "death",
        earnings_by_biome=bot.earnings_by_biome,
    )


__all__ = ["Bot", "RunReport", "simulate_run", "WIN_LIFETIME_EARNINGS"]
