import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clingine.renderer import CursesRenderer  # noqa: E402
from clingine.window import Window  # noqa: E402
from game import menu as menu_module  # noqa: E402
from game.constants import FPS, WINDOW_HEIGHT, WINDOW_WIDTH  # noqa: E402
from game.state import GameState  # noqa: E402


def main() -> None:
    window = Window(WINDOW_WIDTH, WINDOW_HEIGHT, " ", FPS)

    def game_loop() -> None:
        import curses

        # Check color support
        if not curses.has_colors():
            curses.endwin()
            print(
                "Error: Your terminal does not support colors."
                " Please use a color-capable terminal."
            )
            return

        state = GameState()
        state.active_scene = "menu"
        renderer = CursesRenderer(window)

        while window.running:
            dt = window.clock.get_dt()

            # Dispatch by scene
            if state.active_scene == "menu":
                menu_module.update_menu(window, state)
                menu_module.render_menu(renderer, state)
            elif state.active_scene == "game":
                _update_game(window, renderer, state, dt)
            elif state.active_scene == "shop":
                from game import buildings as bld

                bld.update_shop(window, state)
                bld.render_shop(renderer, state)
            elif state.active_scene == "lapidary":
                from game import buildings as bld

                bld.update_lapidary(window, state)
                bld.render_lapidary(renderer, state)
            elif state.active_scene == "save_point":
                from game import buildings as bld

                bld.update_save_point(window, state)
                bld.render_save_point(renderer, state)
            elif state.active_scene == "death":
                menu_module.update_death_screen(window, state)
                menu_module.render_death_screen(renderer, state)
            elif state.active_scene == "win":
                menu_module.update_win_screen(window, state)
                menu_module.render_win_screen(renderer, state)
            elif state.active_scene == "leaderboard":
                menu_module.update_leaderboard(window, state)
                menu_module.render_leaderboard(renderer, state)

            # Always clear keyboard events at end of frame
            window.keyboard.clear_events()
            window.update(FPS)

    def _update_game(window, renderer, state, dt) -> None:
        """Main game scene update + render."""
        from game import buildings as bld
        from game import camera as cam_module
        from game import combat as combat_module
        from game import enemies as enemies_module
        from game import fog as fog_module
        from game import hud as hud_module
        from game import player as player_module
        from game import tools as tools_module

        # Enemy spawning and movement
        enemies_module.spawn_enemies(state, dt)
        enemies_module.update_enemies(state, dt)

        # Combat: enemy auto-attacks
        combat_module.enemy_attacks(state, dt)

        # Input: building interaction check (Space on building tile)
        bld.check_building_interaction(window, state)

        # Update player (movement, HP regen, death check)
        player_module.update_player(window, state, dt)

        # Player attack (F key)
        combat_module.player_attack(window, state)

        # Tool equip (E key) and use (Space key)
        tools_module.update_tools(window, state)
        tools_module.use_tool(window, state)

        # Update fog of war based on current player position
        if state.world_tiles is not None:
            fog_module.update_fog(state)

        # Render world viewport
        if state.world_tiles is not None:
            cam_module.update_camera(state)
            cam_module.render_viewport(renderer, state)

        # Render enemies on top of viewport
        enemies_module.render_enemies(renderer, state)

        # Render player on top of everything
        player_module.render_player(renderer, state)

        # Render HUD
        hud_module.render_hud(renderer, state)

        # ESC opens menu
        if "esc" in window.keyboard.pressed:
            state.active_scene = "menu"

    window.start(game_loop)


if __name__ == "__main__":
    main()
