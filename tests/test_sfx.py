import importlib.util
import io
import pathlib
import wave

from game import events

_SPEC = importlib.util.spec_from_file_location(
    "sfx", pathlib.Path(__file__).parent.parent / "mobile" / "sfx.py"
)
sfx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sfx)

EVENT_KINDS = {
    events.FIND, events.MISS, events.LOOT, events.FULL, events.HIT, events.HURT, events.HEAL,
    events.ACHIEVE, events.COIN, events.DENIED, "detect", "bark", "splash", "pet",
}  # fmt: skip
# Played by the frontend itself, not by an event: the tap, and ambience beds/one-shots.
UI_SOUNDS = {"tap", "rain", "breeze", "cave", "chirp", "cricket", "drip"}
BEDS = {"rain", "breeze", "cave"}


def test_every_event_kind_has_a_sound():
    assert EVENT_KINDS | UI_SOUNDS == set(sfx.SOUNDS)


def test_interface_cues_are_very_short():
    for name in ("tap", "coin", "denied"):
        seconds = sum(segment[3] for segment in sfx.SOUNDS[name])
        assert seconds <= (0.15 if name == "tap" else 0.3), name


def test_sounds_are_short_valid_wavs_and_never_clip():
    for name in sfx.SOUNDS:
        data = sfx.render(name)
        with wave.open(io.BytesIO(data)) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, sfx.RATE)
            limit = 2.5 if name in BEDS else 0.5
            assert 0 < wav.getnframes() / sfx.RATE < limit
            frames = wav.readframes(wav.getnframes())
        peak = max(abs(int.from_bytes(frames[i : i + 2], "little", signed=True))
                   for i in range(0, len(frames), 2))  # fmt: skip
        assert 0 < peak < 32767


def test_rendering_is_deterministic():
    assert sfx.render("hit") == sfx.render("hit")


def test_sounds_are_cached_on_disk(tmp_path):
    paths = sfx.write_sounds(str(tmp_path))
    assert set(paths) == set(sfx.SOUNDS)
    first = pathlib.Path(paths["find"]).stat().st_mtime_ns
    sfx.write_sounds(str(tmp_path))
    assert pathlib.Path(paths["find"]).stat().st_mtime_ns == first


def test_ambience_beds_hold_a_steady_level_and_fade_only_at_the_ends():
    for name in BEDS:
        with wave.open(io.BytesIO(sfx.render(name))) as wav:
            frames = wav.readframes(wav.getnframes())
        values = [int.from_bytes(frames[i : i + 2], "little", signed=True)
                  for i in range(0, len(frames), 2)]  # fmt: skip
        quarter = len(values) // 4
        first = max(abs(v) for v in values[quarter : 2 * quarter])
        last = max(abs(v) for v in values[2 * quarter : 3 * quarter])
        assert abs(values[0]) < 200 and abs(values[-1]) < 200, name  # no click at the seam
        assert first > 0 and 0.4 < last / first < 2.5, name  # no fade in the middle
