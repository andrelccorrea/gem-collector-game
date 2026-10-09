import importlib.util
import json
import pathlib

from game.constants import FPS
from game.hud import BLINK_FRAMES

_SPEC = importlib.util.spec_from_file_location(
    "settings", pathlib.Path(__file__).parent.parent / "mobile" / "settings.py"
)
settings = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(settings)


def test_defaults_and_round_trip(tmp_path):
    path = str(tmp_path / "prefs.json")
    assert settings.load(path) == settings.DEFAULTS
    changed = dict(settings.DEFAULTS, vibration=False, shake=50)
    settings.save(path, changed)
    assert settings.load(path) == changed


def test_bad_or_partial_files_fall_back_to_defaults(tmp_path):
    path = tmp_path / "prefs.json"
    path.write_text(json.dumps({"shake": "loud", "clicks": False}))
    loaded = settings.load(str(path))
    assert loaded["shake"] == 100 and loaded["clicks"] is False
    path.write_text("{not json")
    assert settings.load(str(path)) == settings.DEFAULTS


def test_the_old_single_switch_seeds_sound_vibration_and_ambience(tmp_path):
    loaded = settings.load(str(tmp_path / "none.json"), legacy_sound=False)
    assert not loaded["sound"] and not loaded["vibration"] and not loaded["ambience"]
    assert loaded["clicks"]  # it never covered button clicks


def test_shake_cycles_through_levels_and_switches_toggle():
    assert [settings.next_value("shake", v) for v in (100, 50, 0)] == [50, 0, 100]
    assert settings.next_value("vibration", True) is False
    assert settings.label("shake", 50) == "Screen shake: 50%"
    assert settings.label("reduce_motion", True) == "Reduce motion: on"


def test_hud_blinks_at_most_three_times_a_second():
    assert FPS / (2 * BLINK_FRAMES) <= 3
