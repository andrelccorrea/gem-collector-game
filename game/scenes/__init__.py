"""Scenes: one per screen, dispatched by ``state.active_scene``.

A scene handles input and updates the state (``update``) and draws itself
(``render``). Any code may switch screens by assigning ``state.active_scene``;
the SceneManager notices the change and calls ``enter`` on the new scene.
"""

from game.input import InputState


class Scene:
    def enter(self, state) -> None:
        """Called when this scene becomes active."""

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        raise NotImplementedError

    def render(self, renderer, state) -> None:
        raise NotImplementedError


class FunctionScene(Scene):
    """A scene made of plain ``update(inp, state)`` and ``render(renderer, state)`` functions."""

    def __init__(self, update, render):
        self._update = update
        self._render = render

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        self._update(inp, state)

    def render(self, renderer, state) -> None:
        self._render(renderer, state)


class SceneManager:
    def __init__(self, scenes: dict):
        self.scenes = scenes
        self.current = None

    def frame(self, inp: InputState, state, frame_dt: float, renderer) -> None:
        """Run one frame of the active scene: update, then draw unless it switched away."""
        name = state.active_scene
        scene = self.scenes[name]
        if name != self.current:
            self.current = name
            scene.enter(state)
        scene.update(inp, state, frame_dt)
        if state.active_scene == name:
            scene.render(renderer, state)


def build_scenes() -> dict:
    from game import menu
    from game.scenes import lapidary, save_point, shop, world_map
    from game.scenes.game import GameScene

    return {
        "menu": FunctionScene(menu.update_menu, menu.render_menu),
        "game": GameScene(),
        "shop": FunctionScene(shop.update_shop, shop.render_shop),
        "lapidary": lapidary.LapidaryScene(),
        "save_point": FunctionScene(save_point.update_save_point, save_point.render_save_point),
        "death": FunctionScene(menu.update_death_screen, menu.render_death_screen),
        "win": FunctionScene(menu.update_win_screen, menu.render_win_screen),
        "leaderboard": FunctionScene(menu.update_leaderboard, menu.render_leaderboard),
        # Shares the leaderboard's update: Back returns to the menu.
        "achievements": FunctionScene(menu.update_leaderboard, menu.render_achievements),
        "bestiary": FunctionScene(menu.update_leaderboard, menu.render_bestiary),
        "map": FunctionScene(world_map.update_map, world_map.render_map),
        "daily_end": FunctionScene(menu.update_daily_end, menu.render_daily_end),
        "perks": FunctionScene(menu.update_perks, menu.render_perks),
    }
