from game.constants import (
    COLOR_HUD_BG,
    COLOR_HUD_HP_HIGH,
    COLOR_HUD_HP_LOW,
    COLOR_HUD_HP_MID,
)


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
    biome = _get_biome_name(state)

    row1 = (
        f" HP:{state.player_hp}/{state.player_max_hp}"
        f"  Gold:${state.player_gold}"
        f"  Tool:[{tool}]"
        f"  Biome:{biome}"
    )
    row2_gems = sum(state.inventory.get("gems", {}).values())
    row2 = (
        f" [Arrow]Move [Space]Use [F]Attack [E]Equip [ESC]Menu"
        f"  |  Gems:{row2_gems}  Earned:${state.lifetime_earnings}"
    )

    if state.hud_message and state.hud_message_timer > 0:
        row2 = f" >>> {state.hud_message} <<<"

    _write_hud_str(renderer, row_1, 0, row1[:width], COLOR_HUD_BG)
    _write_hud_str(renderer, row_2, 0, row2[:width], COLOR_HUD_BG)

    hp_text = f"HP:{state.player_hp}/{state.player_max_hp}"
    _write_hud_str(renderer, row_1, 1, hp_text, hp_color)


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


def _get_biome_name(state) -> str:
    from game.constants import BIOME_CAVE_MIN_X, BIOME_MEADOW_MAX_X, TOWN_CENTER_X, TOWN_CENTER_Y

    px, py = state.player_x, state.player_y
    # Check if in town area
    if abs(px - TOWN_CENTER_X) <= 6 and abs(py - TOWN_CENTER_Y) <= 4:
        return "Town"
    if px <= BIOME_MEADOW_MAX_X:
        return "Meadow"
    if px >= BIOME_CAVE_MIN_X:
        return "Cave"
    if py <= 39:  # BIOME_HILLSIDE_MAX_Y
        return "Hillside"
    return "River Delta"
