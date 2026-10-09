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
VERSION = 6  # bump when a sound changes, so cached WAV files are rendered again

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
    # Interface cues: the same family, kept short and quiet (a tap is heard most often).
    "tap": [("sine", 1400, 1200, 0.035, 0.25)],
    "coin": [("square", 1320, 1320, 0.04, 0.25), ("square", 1760, 1760, 0.09, 0.25)],
    "denied": [("square", 180, 150, 0.09, 0.3)],
    "bark": [
        ("noise", 0, 0, 0.03, 0.4),
        ("square", 330, 220, 0.07, 0.4),
        ("silence", 0, 0, 0.05, 0),
        ("square", 330, 220, 0.07, 0.4),
    ],
    "splash": [("noise", 0, 0, 0.06, 0.18)],
    "detect": [("sine", 1050, 1050, 0.05, 0.3), ("sine", 1400, 1400, 0.08, 0.3)],
    # Ambience: looping beds and one-shots scattered over them (played by the frontend).
    "rain": [("hiss", 0, 0, 2.0, 0.5)],
    "breeze": [("hiss", 0, 0, 2.0, 0.15)],
    "cave": [("hum", 70, 70, 2.0, 0.25)],
    "chirp": [
        ("sine", 2600, 3400, 0.06, 0.3),
        ("silence", 0, 0, 0.04, 0),
        ("sine", 2800, 3600, 0.08, 0.3),
    ],
    "cricket": [
        ("square", 4400, 4400, 0.02, 0.12),
        ("silence", 0, 0, 0.03, 0),
        ("square", 4400, 4400, 0.02, 0.12),
        ("silence", 0, 0, 0.03, 0),
        ("square", 4400, 4400, 0.02, 0.12),
    ],
    "drip": [("sine", 1300, 650, 0.07, 0.35)],
    "achievement": [  # little fanfare: C E G C'
        ("square", 523, 523, 0.07, 0.35),
        ("square", 659, 659, 0.07, 0.35),
        ("square", 784, 784, 0.07, 0.35),
        ("square", 1047, 1047, 0.25, 0.4),
    ],
}


# Loops for ambience beds: a steady level with short fades at both ends, so the loop
# point is not heard (one-shots fade out like a pluck instead).
_STEADY = {"hiss", "hum"}


def _segment(shape: str, start: float, end: float, seconds: float, loud: float, rng) -> list:
    count = int(RATE * seconds)
    samples, phase, smooth = [], 0.0, 0.0
    edge = RATE * 0.03
    for i in range(count):
        t = i / max(count - 1, 1)
        phase += 2 * math.pi * (start + (end - start) * t) / RATE
        if shape == "sine":
            value = math.sin(phase)
        elif shape == "square":
            value = 1.0 if math.sin(phase) >= 0 else -1.0
        elif shape == "noise":
            value = rng.uniform(-1, 1)
        elif shape == "hiss":  # soft (low-passed) noise: rain, wind
            smooth = smooth * 0.85 + rng.uniform(-1, 1) * 0.15
            value = smooth * 3
        elif shape == "hum":
            value = math.sin(phase) * 0.7 + math.sin(phase * 1.5) * 0.3
        else:
            value = 0.0
        if shape in _STEADY:
            envelope = min(1.0, i / edge, (count - i) / edge)
        else:
            attack = min(1.0, i / (RATE * 0.004))  # 4 ms fade-in avoids a click
            envelope = attack * (1 - t) ** 2
        samples.append(value * loud * envelope)
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
