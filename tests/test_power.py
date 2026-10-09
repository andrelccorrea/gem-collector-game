import importlib.util
import pathlib

_SPEC = importlib.util.spec_from_file_location(
    "power", pathlib.Path(__file__).parent.parent / "mobile" / "power.py"
)
power = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(power)


def test_targets_by_scene_and_idleness():
    assert power.target_fps("game", 0.0, saver=True) == power.FULL_FPS
    assert power.target_fps("game", power.IDLE_AFTER, saver=True) == power.IDLE_FPS
    assert power.target_fps("shop", 0.0, saver=True) == power.MENU_FPS
    assert power.target_fps("shop", 99.0, saver=False) == power.FULL_FPS


def test_the_rate_eases_down_in_steps_and_jumps_back_up_on_input():
    fps, seen = power.FULL_FPS, []
    for _ in range(5):
        fps = power.next_fps(fps, power.MENU_FPS)
        seen.append(fps)
    assert seen == [25, 20, 15, 15, 15]
    assert power.next_fps(15, power.FULL_FPS) == power.FULL_FPS
    assert power.next_fps(15, power.IDLE_FPS) == 20
    assert min(power.MENU_FPS, power.IDLE_FPS) >= 15  # the floor
