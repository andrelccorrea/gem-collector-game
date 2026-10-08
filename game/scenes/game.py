"""The playable world: fixed-step simulation plus once-per-frame drawing."""

from game import camera, enemies, hud, player
from game.input import InputState
from game.loop import FixedTimestep
from game.scenes import Scene
from game.simulation import step_game


class GameScene(Scene):
    def __init__(self):
        self.timestep = FixedTimestep()

    def enter(self, state) -> None:
        # Game time is frozen while other scenes are shown; drop the time spent there.
        self.timestep.reset()

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        self.timestep.run(frame_dt, inp, lambda step_inp, dt: step_game(step_inp, state, dt))

    def render(self, renderer, state) -> None:
        """Draw the world; runs once per frame regardless of simulation steps."""
        view = camera.render_view(state, renderer)
        camera.render_viewport(renderer, state, view)
        enemies.render_enemies(renderer, state, view)
        player.render_player(renderer, state, view)
        hud.render_hud(renderer, state)
