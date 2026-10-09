"""Player preferences for the Kivy frontend (not part of the game's save).

Following common game-accessibility guidance: vibration apart from sound, ambience and
button clicks apart from effects (some sounds bother some people), screen shake as a
level rather than just on/off, and a reduce-motion switch for the gliding, scrolling,
lunges and shake. Plain data so tests can check it without Kivy.
"""

import json
import os

DEFAULTS = {
    "sound": True,  # event sound effects
    "ambience": True,  # background beds and birdsong
    "clicks": True,  # button taps
    "vibration": True,
    "shake": 100,  # percent
    "reduce_motion": False,
    "zoom": 2,  # world magnification on screen (whole numbers keep pixels even)
    "battery_saver": True,  # fewer frames in menus and when idle (mobile/power.py)
}
SHAKE_STEPS = [100, 50, 0]
ZOOM_STEPS = [2, 3, 1]
LABELS = {
    "sound": "Sound effects",
    "ambience": "Ambience",
    "clicks": "Button clicks",
    "vibration": "Vibration",
    "shake": "Screen shake",
    "reduce_motion": "Reduce motion",
    "zoom": "Zoom",
    "battery_saver": "Battery saver",
}


def load(path: str, legacy_sound=None) -> dict:
    """Saved preferences over the defaults; ``legacy_sound`` is the old single sound and
    vibration switch, used when nothing newer was saved."""
    values = dict(DEFAULTS)
    if legacy_sound is not None:
        values["sound"] = values["vibration"] = values["ambience"] = bool(legacy_sound)
    try:
        with open(path) as f:
            saved = json.load(f)
    except (OSError, ValueError):
        return values
    for key, default in DEFAULTS.items():
        if key in saved and isinstance(saved[key], type(default)):
            values[key] = saved[key]
    return values


def save(path: str, values: dict) -> None:
    tmp = path + ".tmp"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(tmp, "w") as f:
            json.dump(values, f)
        os.replace(tmp, path)
    except OSError:
        pass


def next_value(key: str, value):
    """The value a tap on the setting switches to."""
    steps = {"shake": SHAKE_STEPS, "zoom": ZOOM_STEPS}.get(key)
    if steps:
        return steps[(steps.index(value) + 1) % len(steps)] if value in steps else steps[0]
    return not value


def label(key: str, value) -> str:
    if key == "shake":
        shown = f"{value}%"
    elif key == "zoom":
        shown = f"{value}x"
    else:
        shown = "on" if value else "off"
    return f"{LABELS[key]}: {shown}"
