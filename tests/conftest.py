import pytest

from clingine.renderer import StubRenderer
from game.state import GameState


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Keep saves and the leaderboard of every test out of the real user data dir."""
    path = tmp_path / "data"
    path.mkdir()
    monkeypatch.setenv("GEM_COLLECTOR_DATA_DIR", str(path))
    return path


@pytest.fixture
def stub_renderer():
    return StubRenderer(80, 24)


@pytest.fixture
def game_state():
    state = GameState()
    state.active_scene = "game"
    return state
