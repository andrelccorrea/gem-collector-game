import pytest

from clingine.renderer import StubRenderer
from game.state import GameState


@pytest.fixture
def stub_renderer():
    return StubRenderer(80, 24)


@pytest.fixture
def game_state():
    state = GameState()
    state.active_scene = "game"
    return state
