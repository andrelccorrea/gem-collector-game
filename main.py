import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clingine.renderer import CursesRenderer  # noqa: E402
from clingine.window import Window  # noqa: E402
from game import menu as menu_module  # noqa: E402
from game import persistence  # noqa: E402
from game.constants import FPS, WINDOW_HEIGHT, WINDOW_WIDTH  # noqa: E402
from game.input import map_keys  # noqa: E402
from game.loop import FixedTimestep  # noqa: E402
from game.simulation import step_game  # noqa: E402
from game.state import GameState  # noqa: E402


def main() -> None:
    # Older versions wrote saves to the launch directory (usually next to main.py).
    persistence.import_legacy_files(os.getcwd(), os.path.dirname(os.path.abspath(__file__)))
    window = Window(WINDOW_WIDTH, WINDOW_HEIGHT, " ", FPS)

    def game_loop() -> None:
        import curses

        # Check color support
        if not curses.has_colors():
            curses.endwin()
            print(
                "Error: Your terminal does not support colors. Please use a color-capable terminal."
            )
            return

        state = GameState()
        state.active_scene = "menu"
        renderer = CursesRenderer(window)
        timestep = FixedTimestep()

        while window.running:
            frame_dt = window.clock.tick(FPS)
            window.keyboard.poll()
            inp = map_keys(window.keyboard.pressed)

            # Dispatch by scene
            if state.active_scene == "menu":
                menu_module.update_menu(inp, state)
                menu_module.render_menu(renderer, state)
            elif state.active_scene == "game":
                timestep.run(frame_dt, inp, lambda step_inp, dt: step_game(step_inp, state, dt))
                if state.active_scene == "game":
                    _render_game(renderer, state)
            elif state.active_scene == "shop":
                from game import buildings as bld

                bld.update_shop(inp, state)
                bld.render_shop(renderer, state)
            elif state.active_scene == "lapidary":
                from game import buildings as bld

                bld.update_lapidary(inp, state)
                bld.render_lapidary(renderer, state)
            elif state.active_scene == "save_point":
                from game import buildings as bld

                bld.update_save_point(inp, state)
                bld.render_save_point(renderer, state)
            elif state.active_scene == "death":
                menu_module.update_death_screen(inp, state)
                menu_module.render_death_screen(renderer, state)
            elif state.active_scene == "win":
                menu_module.update_win_screen(inp, state)
                menu_module.render_win_screen(renderer, state)
            elif state.active_scene == "leaderboard":
                menu_module.update_leaderboard(inp, state)
                menu_module.render_leaderboard(renderer, state)

            # Game time is frozen outside the game scene (menus, shop, pause).
            if state.active_scene != "game":
                timestep.reset()

            if state.quit_requested:
                break
            window.update()

    def _render_game(renderer, state) -> None:
        """Draw the game scene; runs once per frame regardless of simulation steps."""
        from game import camera as cam_module
        from game import enemies as enemies_module
        from game import hud as hud_module
        from game import player as player_module

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

    window.start(game_loop)


if __name__ == "__main__":
    main()
