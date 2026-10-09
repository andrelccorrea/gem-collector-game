from game import daylight, weather
from game.constants import (
    COLOR_HUD_BG,
    COLOR_HUD_HP_HIGH,
    COLOR_HUD_HP_LOW,
    COLOR_HUD_HP_MID,
)
from game.gems import bag_capacity, bag_count
from game.geography import region_name
from game.input import Action, hint_label
from game.lantern import LOW_FUEL_SHARE, fuel_share
from game.supplies import supplies_label
from game.tile_info import describe_here

# A changed counter blinks for PULSE_FRAMES drawn frames (~0.5 s at 30 FPS), in the
# color of its change: key -> (color when it went up, color when it went down).
PULSE_FRAMES = 15
BLINK_FRAMES = 6
_PULSE_COLORS = {
    "HP:": (((0, 0, 0), (60, 220, 60)), ((255, 255, 255), (200, 0, 0))),
    "Gold:": (((0, 0, 0), (255, 200, 0)), ((0, 0, 0), (230, 120, 0))),
    "Bag:": (((0, 0, 0), (100, 220, 255)), ((0, 0, 0), (170, 170, 170))),
}


class HudPulse:
    """Remembers the HUD counters between drawn frames and blinks the ones that changed.

    It belongs to whoever draws the HUD (rendering only): the simulation never sees it.
    """

    def __init__(self) -> None:
        self._run_id = None
        self._last: dict = {}
        self._active: dict = {}  # key -> [frames left, went up]

    def update(self, state, values: dict) -> None:
        if state.run_id != self._run_id:  # another run started: nothing "changed"
            self._run_id, self._last, self._active = state.run_id, {}, {}
        for pulse in self._active.values():
            pulse[0] -= 1
        self._active = {k: p for k, p in self._active.items() if p[0] > 0}
        for key, value in values.items():
            old = self._last.get(key)
            if old is not None and value != old:
                self._active[key] = [PULSE_FRAMES, value > old]
            self._last[key] = value

    def color(self, key: str) -> tuple | None:
        """The counter's highlight this frame, or None (also during the blink's off beat)."""
        pulse = self._active.get(key)
        # Half a blink lasts BLINK_FRAMES: 2.5 flashes a second at 30 FPS, under the
        # 3-per-second limit for flashing content.
        if pulse is None or ((PULSE_FRAMES - pulse[0]) // BLINK_FRAMES) % 2 == 1:
            return None
        up, down = _PULSE_COLORS[key]
        return up if pulse[1] else down


def render_hud(renderer, state, pulse: HudPulse | None = None) -> None:
    """Draw the three status rows at the bottom of the screen: status, the player's
    tile, then key hints (or the latest message, with the bag fill kept at the end).
    With a ``pulse``, counters that changed since the last frame blink."""
    width = renderer.width
    row_1, row_here, row_2 = renderer.height - 3, renderer.height - 2, renderer.height - 1
    if row_1 < 0:
        return

    for row in (row_1, row_here, row_2):
        for x in range(width):
            renderer.set_cell(x, row, " ", COLOR_HUD_BG)

    hp_pct = state.player_hp / max(state.player_max_hp, 1)
    if hp_pct > 0.5:
        hp_color = COLOR_HUD_HP_HIGH
    elif hp_pct > 0.25:
        hp_color = COLOR_HUD_HP_MID
    else:
        hp_color = COLOR_HUD_HP_LOW

    tool = state.equipped_tool or "none"
    biome = region_name(state.player_x, state.player_y)

    row1 = (
        f" HP:{state.player_hp}/{state.player_max_hp}"
        f"  Gold:${state.player_gold}"
        f"  Tool:[{tool}]"
        f"  Biome:{biome}"
        f"  Light:{round(fuel_share(state) * 100)}%" + (_daily_clock(state) if state.daily else "")
    )
    sky = daylight.phase(state)[0].title() if daylight.phase(state)[0] != "day" else ""
    if weather.rain_here(state):
        sky = f"{sky} rain".strip().capitalize()
    if sky and len(row1) + len(sky) + 2 <= width:
        row1 += f"  {sky}"
    carried, capacity = bag_count(state), bag_capacity(state)
    row2 = (
        " "
        + " ".join(
            hint_label(action, verb)
            for action, verb in (
                (Action.USE, "Use"),
                (Action.ATTACK, "Attack"),
                (Action.CYCLE_TOOL, "Tool"),
                (Action.RECALL, "Recall"),
                (Action.CANCEL, "Menu"),
            )
        )
        + f"  |  Bag:{carried}/{capacity}  Earned:${state.lifetime_earnings}"
    )

    if state.hud_message and state.hud_message_timer > 0:
        row2 = f" >>> {state.hud_message} <<<"
        bag = f"Bag:{carried}/{capacity} "
        if len(row2) + len(bag) + 2 <= width:
            row2 += bag.rjust(width - len(row2))

    _write_hud_str(renderer, row_1, 0, row1[:width], COLOR_HUD_BG)
    here = f" {describe_here(state)}"
    carried_supplies = supplies_label(state)
    if carried_supplies:
        tag = f"{hint_label(Action.USE_ITEM, 'Item')}:{carried_supplies} "
        if len(here) + len(tag) + 2 <= width:
            here += tag.rjust(width - len(here))
    _write_hud_str(renderer, row_here, 0, here[:width], COLOR_HUD_BG)
    _write_hud_str(renderer, row_2, 0, row2[:width], COLOR_HUD_BG)

    hp_text = f"HP:{state.player_hp}/{state.player_max_hp}"
    _write_hud_str(renderer, row_1, 1, hp_text, hp_color)

    if fuel_share(state) < LOW_FUEL_SHARE:
        light_at = row1.find("Light:")
        _write_hud_str(renderer, row_1, light_at, row1[light_at:], COLOR_HUD_HP_LOW)

    if pulse is not None:
        pulse.update(state, {"HP:": state.player_hp, "Gold:": state.player_gold, "Bag:": carried})
        for row, text in ((row_1, row1[:width]), (row_2, row2[:width])):
            for key in _PULSE_COLORS:
                color = pulse.color(key)
                at = text.find(key)
                if color is not None and at >= 0:
                    end = text.find(" ", at)
                    _write_hud_str(renderer, row, at, text[at : end if end > 0 else None], color)


def _write_hud_str(renderer, y: int, x: int, text: str, color_pair: tuple) -> None:
    if not 0 <= y < renderer.height:
        return
    for i, ch in enumerate(text):
        cx = x + i
        if cx >= renderer.width:
            break
        existing_char, existing_cp = renderer.get_cell(cx, y)
        if existing_char != ch or existing_cp != color_pair:
            renderer.set_cell(cx, y, ch, color_pair)


def _daily_clock(state) -> str:
    from game.daily import time_left

    minutes, seconds = divmod(int(time_left(state)), 60)
    return f"  Time:{minutes}:{seconds:02d}"
