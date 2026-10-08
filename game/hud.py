from game.constants import (
    COLOR_HUD_BG,
    COLOR_HUD_HP_HIGH,
    COLOR_HUD_HP_LOW,
    COLOR_HUD_HP_MID,
)
from game.gems import bag_capacity, bag_count
from game.geography import region_name
from game.lantern import LOW_FUEL_SHARE, fuel_share


def render_hud(renderer, state) -> None:
    """Draw the two status rows at the bottom of the screen."""
    width = renderer.width
    row_1, row_2 = renderer.height - 2, renderer.height - 1
    if row_1 < 0:
        return

    for row in (row_1, row_2):
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
    carried, capacity = bag_count(state), bag_capacity(state)
    row2 = (
        f" [Arrow]Move [Space]Use [F]Attack [E]Equip [ESC]Menu"
        f"  |  Bag:{carried}/{capacity}  Earned:${state.lifetime_earnings}"
    )

    if state.hud_message and state.hud_message_timer > 0:
        row2 = f" >>> {state.hud_message} <<<"

    _write_hud_str(renderer, row_1, 0, row1[:width], COLOR_HUD_BG)
    _write_hud_str(renderer, row_2, 0, row2[:width], COLOR_HUD_BG)

    hp_text = f"HP:{state.player_hp}/{state.player_max_hp}"
    _write_hud_str(renderer, row_1, 1, hp_text, hp_color)

    if fuel_share(state) < LOW_FUEL_SHARE:
        light_at = row1.find("Light:")
        _write_hud_str(renderer, row_1, light_at, row1[light_at:], COLOR_HUD_HP_LOW)


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
