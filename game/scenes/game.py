"""The playable world: fixed-step simulation plus once-per-frame drawing."""

from game import achievements, camera, critters, enemies, hud, player, profile
from game.input import InputState
from game.loop import FixedTimestep
from game.scenes import Scene
from game.simulation import step_game


class GameScene(Scene):
    def __init__(self):
        self.timestep = FixedTimestep()
        self.hud_pulse = hud.HudPulse()
        self._tips_saved: set = set()
        self._achieved: set = set()

    def enter(self, state) -> None:
        # Game time is frozen while other scenes are shown; drop the time spent there.
        self.timestep.reset()
        # Tips shown in earlier runs (or sessions) are not shown again.
        saved = profile.load_profile()
        state.tips_seen |= set(saved["tips"])
        self._tips_saved = set(state.tips_seen)
        self._achieved = set(saved["achievements"])
        state.outfit = saved["outfit"]

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        self.timestep.run(frame_dt, inp, lambda step_inp, dt: step_game(step_inp, state, dt))
        new = achievements.newly_unlocked(state, self._achieved)
        if new:
            rewards = {a[0]: a[3] for a in achievements.ACHIEVEMENTS}
            profile.unlock_achievements(new, rewards)
            self._achieved |= set(new)
            for achievement_id in new:
                achievements.announce(state, achievement_id)
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
