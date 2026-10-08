"""The playable world: fixed-step simulation plus once-per-frame drawing."""

from game import camera, critters, enemies, hud, player, profile
from game.input import InputState
from game.loop import FixedTimestep
from game.scenes import Scene
from game.simulation import step_game


class GameScene(Scene):
    def __init__(self):
        self.timestep = FixedTimestep()
        self.hud_pulse = hud.HudPulse()
        self._tips_saved: set = set()

    def enter(self, state) -> None:
        # Game time is frozen while other scenes are shown; drop the time spent there.
        self.timestep.reset()
        # Tips shown in earlier runs (or sessions) are not shown again.
        state.tips_seen |= set(profile.load_profile()["tips"])
        self._tips_saved = set(state.tips_seen)

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        self.timestep.run(frame_dt, inp, lambda step_inp, dt: step_game(step_inp, state, dt))
        if state.tips_seen != self._tips_saved:
            profile.remember_tips(state.tips_seen)
            self._tips_saved = set(state.tips_seen)

    def render(self, renderer, state) -> None:
        """Draw the world; runs once per frame regardless of simulation steps."""
        view = camera.render_view(state, renderer)
        camera.render_viewport(renderer, state, view)
        critters.render_critters(renderer, state, view)
        enemies.render_enemies(renderer, state, view)
        player.render_player(renderer, state, view)
        hud.render_hud(renderer, state, self.hud_pulse)
