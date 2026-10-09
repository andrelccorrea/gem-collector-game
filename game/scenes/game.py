"""The playable world: fixed-step simulation plus once-per-frame drawing."""

from game import (
    achievements,
    bestiary,
    camera,
    critters,
    dog,
    enemies,
    goals,
    hud,
    merchant,
    player,
    profile,
    townsfolk,
    weather,
)
from game.input import InputState
from game.loop import FixedTimestep
from game.player import set_hud_message
from game.scenes import Scene
from game.simulation import step_game

STATS_SYNC_SECONDS = 15.0  # real seconds between lifetime-stat writes while playing


class GameScene(Scene):
    def __init__(self):
        self.timestep = FixedTimestep()
        self.hud_pulse = hud.HudPulse()
        self._tips_saved: set = set()
        self._achieved: set = set()
        self._friends_saved: set = set()
        self._synced: dict = {}  # state.stats as last added to the profile
        self._synced_run = None
        self._synced_at = 0.0

    def enter(self, state) -> None:
        # Game time is frozen while other scenes are shown; drop the time spent there.
        self.timestep.reset()
        # Tips shown in earlier runs (or sessions) are not shown again.
        saved = profile.load_profile()
        state.tips_seen |= set(saved["tips"])
        self._tips_saved = set(state.tips_seen)
        self._achieved = set(saved["achievements"])
        if state.run_id != self._synced_run:  # another run: its counters start afresh
            self._synced, self._synced_run = dict(state.stats), state.run_id
        state.outfit = saved["outfit"]
        state.seen_species = set(saved["bestiary"])
        state.friends |= set(saved["friends"])
        state.goal = max(state.goal, saved["goal"])
        if state.game_time == 0 and goals.current(state) and not state.hud_message:
            set_hud_message(state, f"Goal: {goals.current(state)}", 5.0)
        self._friends_saved = set(state.friends)

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        self.timestep.run(frame_dt, inp, lambda step_inp, dt: step_game(step_inp, state, dt))
        sighted = bestiary.seen_now(state) - state.seen_species
        if sighted:
            profile.record_sightings(sighted, bestiary.context(state))
            for name in sorted(sighted):
                state.seen_species.add(name)
                bestiary.announce(state, name, len(state.seen_species))
        if goals.check(state):
            profile.record_goal(state.goal)
        if state.friends != self._friends_saved:
            profile.record_friends(state.friends)
            self._friends_saved = set(state.friends)
        new = achievements.newly_unlocked(state, self._achieved)
        if new:
            rewards = {a[0]: a[3] for a in achievements.ACHIEVEMENTS}
            profile.unlock_achievements(new, rewards)
            self._achieved |= set(new)
            for achievement_id in new:
                achievements.announce(state, achievement_id)
        self._synced_at += frame_dt
        if self._synced_at >= STATS_SYNC_SECONDS or state.active_scene != "game":
            self.sync_stats(state)
        if state.tips_seen != self._tips_saved:
            profile.remember_tips(state.tips_seen)
            self._tips_saved = set(state.tips_seen)

    def sync_stats(self, state) -> None:
        """Add what the run's counters gained since last time to the lifetime totals."""
        self._synced_at = 0.0
        if state.run_id != self._synced_run:
            self._synced, self._synced_run = {}, state.run_id
        deltas = {k: v - self._synced.get(k, 0) for k, v in state.stats.items()}
        profile.add_stats(deltas)
        self._synced = dict(state.stats)

    def render(self, renderer, state) -> None:
        """Draw the world; runs once per frame regardless of simulation steps."""
        view = camera.render_view(state, renderer)
        camera.render_viewport(renderer, state, view)
        critters.render_critters(renderer, state, view)
        dog.render_dog(renderer, state, view)
        townsfolk.render_townsfolk(renderer, state, view)
        merchant.render_cart(renderer, state, view)
        enemies.render_enemies(renderer, state, view)
        player.render_player(renderer, state, view)
        weather.render_rain(renderer, state, view)
        hud.render_hud(renderer, state, self.hud_pulse)
