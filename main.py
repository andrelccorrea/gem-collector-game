import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from clingine.renderer import CursesRenderer  # noqa: E402
from clingine.window import Window  # noqa: E402
from game import persistence  # noqa: E402
from game.constants import FPS, WINDOW_HEIGHT, WINDOW_WIDTH  # noqa: E402
from game.input import map_keys  # noqa: E402
from game.scenes import SceneManager, build_scenes  # noqa: E402
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
        scenes = SceneManager(build_scenes())

        while window.running:
            frame_dt = window.clock.tick(FPS)
            window.keyboard.poll()
            scenes.frame(map_keys(window.keyboard.pressed), state, frame_dt, renderer)
            if state.quit_requested:
                break
            window.update()

    window.start(game_loop)


if __name__ == "__main__":
    main()
