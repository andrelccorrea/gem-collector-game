"""Sound effects synthesized in code (8-bit style), one per event kind in game/events.py.

No audio files ship with the game: ``write_sounds`` renders each effect to a WAV file
once (in a cache folder), and the frontend plays them. Standard library only, so tests
can check it without Kivy.
"""

import io
import math
import os
import random
import struct
import wave

RATE = 22050
VOLUME = 0.45
VERSION = 1  # bump when a sound changes, so cached WAV files are rendered again

# Each sound is a list of segments: (wave, start Hz, end Hz, seconds, loudness).
# The pitch slides from start to end; every segment fades out (a "pluck").
SOUNDS = {
    "find": [  # bright rising arpeggio: a gem
        ("sine", 880, 880, 0.06, 0.8),
        ("sine", 1320, 1320, 0.06, 0.8),
        ("sine", 1760, 1760, 0.16, 0.9),
    ],
    "miss": [("sine", 140, 70, 0.12, 0.9), ("noise", 0, 0, 0.05, 0.25)],  # dull thud
    "loot": [("square", 660, 660, 0.05, 0.4), ("square", 990, 990, 0.09, 0.4)],
    "full": [  # two low "no" beeps
        ("square", 220, 220, 0.08, 0.4),
        ("silence", 0, 0, 0.04, 0),
        ("square", 196, 196, 0.12, 0.4),
    ],
    "hit": [("noise", 0, 0, 0.05, 0.7), ("sine", 200, 90, 0.08, 0.8)],  # punch
    "hurt": [("square", 320, 140, 0.18, 0.5)],  # falling buzz
    "heal": [("sine", 520, 780, 0.2, 0.5)],  # soft rise
    "achievement": [  # little fanfare: C E G C'
        ("square", 523, 523, 0.07, 0.35),
        ("square", 659, 659, 0.07, 0.35),
        ("square", 784, 784, 0.07, 0.35),
        ("square", 1047, 1047, 0.25, 0.4),
    ],
}


def _segment(shape: str, start: float, end: float, seconds: float, loud: float, rng) -> list:
    count = int(RATE * seconds)
    samples, phase = [], 0.0
    for i in range(count):
        t = i / max(count - 1, 1)
        phase += 2 * math.pi * (start + (end - start) * t) / RATE
        if shape == "sine":
            value = math.sin(phase)
        elif shape == "square":
            value = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "noise":
            value = rng.uniform(-1, 1)
        else:
            value = 0.0
        attack = min(1.0, i / (RATE * 0.004))  # 4 ms fade-in avoids a click
        samples.append(value * loud * attack * (1 - t) ** 2)
    return samples


def render(name: str) -> bytes:
    """The sound as a 16-bit mono WAV file."""
    rng = random.Random(name)  # the same noise every time
    samples = []
    for segment in SOUNDS[name]:
        samples += _segment(*segment, rng)
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s * VOLUME)) * 32767)) for s in samples
    )
    out = io.BytesIO()
    with wave.open(out, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(frames)
    return out.getvalue()


def write_sounds(folder: str) -> dict:
    """Render every sound into ``folder`` (only those not cached yet): name -> path."""
    os.makedirs(folder, exist_ok=True)
    paths = {}
    for name in SOUNDS:
        path = os.path.join(folder, f"{name}-v{VERSION}.wav")
        if not os.path.exists(path):
            with open(path + ".tmp", "wb") as f:
                f.write(render(name))
            os.replace(path + ".tmp", path)
        paths[name] = path
    return paths
