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
    events.FIND, events.MISS, events.LOOT, events.FULL, events.HIT, events.HURT, events.HEAL
}  # fmt: skip


def test_every_event_kind_has_a_sound():
    assert EVENT_KINDS == set(sfx.SOUNDS)


def test_sounds_are_short_valid_wavs_and_never_clip():
    for name in sfx.SOUNDS:
        data = sfx.render(name)
        with wave.open(io.BytesIO(data)) as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, sfx.RATE)
            assert 0 < wav.getnframes() / sfx.RATE < 0.5
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
