"""Gem Collector: Kivy frontend (Android, also runs on the desktop for testing).

The game itself is the same package the terminal version uses. This file only:
draws the 80x24 cell grid with Kivy (pixel-art sprites from sprites.py where the game
sets them, characters elsewhere), turns touches/buttons/keys into InputState
(game/touch.py), and handles the Android lifecycle (save on pause, back button).

Desktop:  .venv-mobile/bin/python mobile/main.py
Android:  see docs/ANDROID.md
"""

import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# In the Android package the game sources are copied next to this file; during
# development they live one directory up.
sys.path.insert(0, HERE if os.path.isdir(os.path.join(HERE, "game")) else os.path.dirname(HERE))

from kivy.config import Config  # noqa: E402

# Esc / the Android back button closes screens in the game instead of the app.
Config.set("kivy", "exit_on_escape", "0")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.audio import SoundLoader  # noqa: E402
from kivy.core.text import Label as CoreLabel  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.graphics import (  # noqa: E402
    Color,
    InstructionGroup,
    PopMatrix,
    PushMatrix,
    Rectangle,
    Translate,
)
from kivy.graphics.scissor_instructions import ScissorPop, ScissorPush  # noqa: E402
from kivy.graphics.texture import Texture  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.storage.jsonstore import JsonStore  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.gridlayout import GridLayout  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402
from particles import burst, step  # noqa: E402
from sfx import write_sounds  # noqa: E402
from sprites import HEIGHT as SPRITE_HEIGHT  # noqa: E402
from sprites import WIDTH as SPRITE_WIDTH  # noqa: E402
from sprites import facing, frame_at, sprite_rgba, walk_frame  # noqa: E402

from clingine.renderer import Renderer  # noqa: E402
from game import camera, daylight, persistence, weather  # noqa: E402
from game.constants import FPS, HUD_ROWS, MOVE_COOLDOWN  # noqa: E402
from game.events import COIN, DENIED, FIND, HIT, HURT, take_events  # noqa: E402
from game.geography import biome_at  # noqa: E402
from game.input import Action, InputState, map_keys, set_hints  # noqa: E402
from game.scenes import SceneManager, build_scenes  # noqa: E402
from game.state import GameState  # noqa: E402
from game.theme import ASCII_FALLBACK  # noqa: E402
from game.touch import TouchController  # noqa: E402

COLS, ROWS = 80, 24
WORLD_ROWS = ROWS - HUD_ROWS  # the world view; the HUD rows below never scroll
# On-screen hints name the touch buttons instead of keys.
TOUCH_HINTS = {
    Action.MOVE_UP: "^",
    Action.MOVE_DOWN: "v",
    Action.MOVE_LEFT: "<",
    Action.MOVE_RIGHT: ">",
    Action.USE: "Use",
    Action.ATTACK: "Attack",
    Action.CYCLE_TOOL: "Tool",
    Action.NEXT_TAB: "Tab",
    Action.CONFIRM: "OK",
    Action.CANCEL: "Back",
    Action.RECALL: "Recall",
    Action.USE_ITEM: "Item",
    Action.MAP: "Map",
}
DEFAULT_BG = (0, 0, 0)
DEFAULT_FG = (255, 255, 255)

# Kivy key codes -> the key names DEFAULT_KEYMAP understands (letters map to themselves).
_KEY_NAMES = {273: "up", 274: "down", 276: "left", 275: "right", 32: "space",
              13: "enter", 271: "enter", 27: "esc", 9: "tab"}  # fmt: skip


class GridRenderer(Renderer):
    """A COLS x ROWS character grid that remembers which cells changed since the
    last draw (the curses version's screen_array, without curses)."""

    def __init__(self):
        self._cells = [[(" ", None)] * COLS for _ in range(ROWS)]
        self.dirty = {(x, y) for y in range(ROWS) for x in range(COLS)}
        # Sprites set this frame: (x, y) -> {layer: (sprite, tint)}; emptied by each flush.
        self.sprites: dict = {}
        # Moving things set this frame: entity -> (x, y, sprite, tint), drawn by EntityLayer.
        self.entities: dict = {}

    @property
    def width(self) -> int:
        return COLS

    @property
    def height(self) -> int:
        return ROWS

    def set_cell(self, x, y, char, color_pair):
        if 0 <= x < COLS and 0 <= y < ROWS and self._cells[y][x] != (char, color_pair):
            self._cells[y][x] = (char, color_pair)
            self.dirty.add((x, y))

    def get_cell(self, x, y):
        return self._cells[y][x]

    def clear(self, color_pair=None):
        for y in range(ROWS):
            for x in range(COLS):
                self.set_cell(x, y, " ", color_pair)

    def set_sprite(self, x, y, layer, sprite, tint, entity=None):
        if not (0 <= x < COLS and 0 <= y < ROWS):
            return
        if entity is not None:
            self.entities[entity] = (x, y, sprite, tint)
        else:
            self.sprites.setdefault((x, y), {})[layer] = (sprite, tint)


def _rgba(rgb):
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1)


_WHITE = (255, 255, 255)
_textures: dict = {}


def _sprite_texture(sprite, frame=0):
    """The texture of one frame of a sprite (built once, scaled without smoothing), or None."""
    key = (sprite, frame)
    if key not in _textures:
        pixels = sprite_rgba(sprite, frame)
        texture = None
        if pixels is not None:
            texture = Texture.create(size=(SPRITE_WIDTH, SPRITE_HEIGHT), colorfmt="rgba")
            texture.blit_buffer(pixels, colorfmt="rgba", bufferfmt="ubyte")
            texture.mag_filter = texture.min_filter = "nearest"
        _textures[key] = texture
    return _textures[key]


class GridView(Widget):
    """Draws a GridRenderer: per cell, a background rectangle (solid color or ground
    sprite) and a foreground one (glyph or object sprite)."""

    def __init__(self, tap_handler, **kwargs):
        super().__init__(**kwargs)
        self.tap_handler = tap_handler
        self._glyphs: dict = {}
        self._bg, self._fg = [], []
        with self.canvas.before:
            PushMatrix()
            self.shake = Translate(0, 0)  # screen shake moves the whole grid
        with self.canvas:
            # The world rows slide (smooth scrolling), clipped so they never cover the HUD.
            self._clip = ScissorPush()
            PushMatrix()
            self.scroll = Translate(0, 0)
            for i in range(ROWS * COLS):
                if i == WORLD_ROWS * COLS:
                    PopMatrix()
                    ScissorPop()
                self._bg.append((Color(0, 0, 0, 1), Rectangle()))
                self._fg.append((Color(1, 1, 1, 1), Rectangle()))
        self.overlay = InstructionGroup()  # floating texts, redrawn every frame
        self.canvas.after.add(self.overlay)
        self.canvas.after.add(PopMatrix())
        self.bind(pos=self._layout, size=self._layout)
        self._renderer = None
        self._shown_sprites: dict = {}

    def cell_size(self):
        return self.width / COLS, self.height / ROWS

    def _layout(self, *_):
        cw, ch = self.cell_size()
        self._glyphs.clear()  # font size follows the cell size
        for y in range(ROWS):
            for x in range(COLS):
                i = y * COLS + x
                pos = (self.x + x * cw, self.top - (y + 1) * ch)
                self._bg[i][1].pos, self._bg[i][1].size = pos, (cw, ch)
                self._fg[i][1].pos = pos
        world_h = WORLD_ROWS * ch
        clip = self._clip
        clip.x, clip.y = int(self.x), int(self.top - world_h)
        clip.width, clip.height = int(self.width), int(world_h)
        if self._renderer is not None:
            self._renderer.dirty = {(x, y) for y in range(ROWS) for x in range(COLS)}
        self._shown_sprites = {}

    def _glyph(self, char):
        texture = self._glyphs.get(char)
        if texture is None:
            cw, ch = self.cell_size()
            # RobotoMono glyphs are 0.6 em wide: fit both the cell height and width.
            size = max(min(ch * 0.85, cw / 0.6 * 0.95), 6)
            # RobotoMono lacks the terminal theme's symbols; the ASCII originals stand in.
            text = ASCII_FALLBACK.get(char, char)
            label = CoreLabel(text=text, font_size=size, font_name="RobotoMono-Regular")
            label.refresh()
            texture = self._glyphs[char] = label.texture
        return texture

    def flush(self, renderer: GridRenderer) -> None:
        """Update only the cells whose character or sprites changed since the last flush."""
        self._renderer = renderer
        sprites, renderer.sprites = renderer.sprites, {}
        # Each layer becomes (sprite, tint, frame): an animation step is then just another
        # change of the cell, redrawn like any other.
        now = time.perf_counter()
        for (x, y), layers in sprites.items():
            phase = x * 7 + y * 13
            for layer, (sprite, tint) in layers.items():
                layers[layer] = (sprite, tint, frame_at(sprite, now, phase))
        changed = renderer.dirty
        for cell in sprites.keys() | self._shown_sprites.keys():
            if sprites.get(cell) != self._shown_sprites.get(cell):
                changed.add(cell)
        self._shown_sprites = sprites
        cw, ch = self.cell_size()
        for x, y in changed:
            char, colors = renderer.get_cell(x, y)
            fg, bg = colors if colors else (DEFAULT_FG, DEFAULT_BG)
            i = y * COLS + x
            layers = sprites.get((x, y), {})
            ground = self._sprite(layers.get("ground"))
            bg_color, bg_rect = self._bg[i]
            bg_color.rgba = _rgba(ground[1] if ground else bg)
            bg_rect.texture = ground[0] if ground else None
            color, rect = self._fg[i]
            obj = self._sprite(layers.get("object"))
            if obj:
                color.rgba = _rgba(obj[1])
                rect.texture = obj[0]
                rect.size = (cw, ch)
                rect.pos = (self.x + x * cw, self.top - (y + 1) * ch)
            # The glyph shows where no sprite covers it (no ground sprite, or an object
            # that has no image).
            elif char.strip() and (not ground or "object" in layers):
                texture = self._glyph(char)
                color.rgba = _rgba(fg)
                rect.texture = texture
                tw, th = texture.size
                rect.size = (tw, th)
                rect.pos = (
                    self.x + x * cw + (cw - tw) / 2,
                    self.top - (y + 1) * ch + (ch - th) / 2,
                )
            else:
                rect.size = (0, 0)
        renderer.dirty = set()

    @staticmethod
    def _sprite(layer):
        """(texture, tint) for a (sprite, tint, frame) layer, or None if it has no sprite."""
        if layer is None:
            return None
        texture = _sprite_texture(layer[0], layer[2])
        return (texture, layer[1] or _WHITE) if texture is not None else None

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        cw, ch = self.cell_size()
        x = int((touch.x - self.x) / cw)
        y = int((self.top - touch.y) / ch)
        self.tap_handler(x, y)
        return True


FLOAT_SECONDS = 1.2  # how long an event's text stays up
FLOAT_RISE = 1.5  # cells it rises in that time
FLOAT_STACK_SECONDS = 0.3  # events this close on one tile stack instead of overlapping


class FloatingTexts:
    """World events (game/events.py) as text with an icon that rises from its tile and
    fades out, drawn over the grid. Only shown while the world is on screen."""

    def __init__(self, grid: GridView):
        self.grid = grid
        self.items: list = []  # (event, born, stack slot)
        self._labels: dict = {}
        self._font_size = None

    def add(self, events, now: float) -> None:
        for event in events:
            if not event.text:  # interface cues (coin, denied) have nothing to show
                continue
            slot = sum(
                1
                for other, born, _ in self.items
                if (other.x, other.y) == (event.x, event.y) and now - born < FLOAT_STACK_SECONDS
            )
            self.items.append((event, now, slot))

    def _label(self, text: str, size: float):
        if size != self._font_size:
            self._labels.clear()
            self._font_size = size
        texture = self._labels.get(text)
        if texture is None:
            label = CoreLabel(text=text, font_size=size, font_name="RobotoMono-Regular",
                              bold=True, outline_width=2, outline_color=(0, 0, 0))  # fmt: skip
            label.refresh()
            texture = self._labels[text] = label.texture
        return texture

    def draw(self, view, now: float) -> None:
        """Add this frame's texts to the grid overlay (cleared by the caller)."""
        overlay = self.grid.overlay
        self.items = [item for item in self.items if now - item[1] < FLOAT_SECONDS]
        if view is None:
            return
        grid = self.grid
        cw, ch = grid.cell_size()
        for event, born, slot in self.items:
            if not view.contains(event.x, event.y):
                continue
            age = (now - born) / FLOAT_SECONDS
            alpha = 1.0 if age < 0.6 else (1.0 - age) / 0.4
            label = self._label(event.text, max(ch * 0.8, 8))
            icon = _sprite_texture(event.icon) if event.icon else None
            icon_w = cw * 1.4 if icon else 0
            width = icon_w + label.width
            center_x = grid.x + (event.x - view.x + 0.5) * cw + grid.scroll.x
            left = min(max(center_x - width / 2, grid.x), grid.right - width)
            bottom = grid.top - (event.y - view.y) * ch + (slot + age * FLOAT_RISE) * ch
            bottom += grid.scroll.y
            if icon:
                overlay.add(Color(*_rgba(event.color or _WHITE)[:3], alpha))
                overlay.add(Rectangle(texture=icon, pos=(left, bottom), size=(icon_w, ch * 1.4)))
            overlay.add(Color(*_rgba(event.text_color)[:3], alpha))
            text_y = bottom + (ch * 1.4 - label.height) / 2
            overlay.add(Rectangle(texture=label, pos=(left + icon_w, text_y), size=label.size))


SLIDE_SECONDS = MOVE_COOLDOWN  # one step's slide ends as the next step may begin


class WorldSlide:
    """Smooth scrolling: when the camera steps, the world is drawn where it was and slides
    to its new place at constant speed, so walking reads as one continuous motion."""

    def __init__(self, grid: GridView):
        self.grid = grid
        self.last = None
        self.origin = (0.0, 0.0)  # offset at the start of the current slide
        self.start = 0.0

    def update(self, view, now: float) -> None:
        if view is None:  # world not on screen: nothing to slide
            self.last, self.origin = None, (0.0, 0.0)
        elif self.last is not None:
            dx, dy = view.x - self.last.x, view.y - self.last.y
            if (dx or dy) and abs(dx) <= 1 and abs(dy) <= 1:  # a step, not a teleport
                cw, ch = self.grid.cell_size()
                x, y = self.grid.scroll.xy
                self.origin, self.start = (x + dx * cw, y - dy * ch), now
            elif dx or dy:
                self.origin = (0.0, 0.0)
        self.last = view
        left = 1.0 - min(1.0, (now - self.start) / SLIDE_SECONDS)
        self.grid.scroll.xy = (self.origin[0] * left, self.origin[1] * left)


SHAKE_SECONDS = 0.2  # the grid shakes this long when the player is hurt
SHAKE_CELLS = 0.3  # starting amplitude, in cells; it eases out to zero
VIBRATE_MS = {HURT: 40, FIND: 20, COIN: 12, DENIED: 25}  # Android only


class ScreenShake:
    """Shakes the grid briefly (a small, fast-fading random offset) after a hit."""

    def __init__(self, grid: GridView):
        self.grid = grid
        self.until = 0.0
        self._rng = random.Random()  # visual only: never the game's RNG

    def update(self, events, now: float) -> None:
        if any(event.kind == HURT for event in events):
            self.until = now + SHAKE_SECONDS
        left = max(0.0, self.until - now) / SHAKE_SECONDS
        amplitude = SHAKE_CELLS * self.grid.cell_size()[0] * left**2
        self.grid.shake.xy = (
            self._rng.uniform(-amplitude, amplitude),
            self._rng.uniform(-amplitude, amplitude),
        )


def _android_vibrator():
    """Android's Vibrator service, or None elsewhere (desktop) or if it is unavailable."""
    try:
        from jnius import autoclass

        activity = autoclass("org.kivy.android.PythonActivity").mActivity
        context = autoclass("android.content.Context")
        return activity.getSystemService(context.VIBRATOR_SERVICE)
    except Exception:  # no pyjnius / not on Android
        return None


TWEEN_MAX = 0.15  # longest glide between two cells (one player step)
LUNGE = 0.35  # cells the player steps toward what it hits
RECOIL = 0.3  # cells a hit enemy is pushed back (then it settles)
TWEEN_MIN = 0.06


class EntityLayer:
    """Draws moving things (player, enemies, animals) gliding between cells.

    The game's position stays the truth; the drawn position starts where the thing was
    and eases to the new cell over about the time between its steps (at most one player
    step), so steady walking looks continuous. Jumps of more than one cell snap.
    """

    def __init__(self, grid: GridView):
        self.grid = grid
        # entity -> [from_x, from_y, to_x, to_y, start, duration, facing (1 right, -1 left)]
        self.tracks: dict = {}
        self.nudges: dict = {}  # entity -> (dx, dy, start, duration): out-and-back offset

    def react(self, events, now: float) -> None:
        """Melee feedback: the player lunges at what it hits, and the target recoils."""
        player = self.tracks.get("player")
        for event in events:
            if event.kind != HIT or player is None:
                continue
            dx = (event.x > player[2]) - (event.x < player[2])
            dy = (event.y > player[3]) - (event.y < player[3])
            self.nudges["player"] = (dx * LUNGE, dy * LUNGE, now, 0.14)
            for entity, track in self.tracks.items():
                if entity != "player" and (track[2], track[3]) == (event.x, event.y):
                    self.nudges[entity] = (dx * RECOIL, dy * RECOIL, now, 0.18)

    def _nudge(self, entity, now: float) -> tuple:
        nudge = self.nudges.get(entity)
        if nudge is None:
            return 0.0, 0.0
        dx, dy, start, duration = nudge
        t = (now - start) / duration
        if t >= 1:
            del self.nudges[entity]
            return 0.0, 0.0
        push = math.sin(math.pi * t)  # out and back
        jitter = 0.06 * math.sin(t * 40) if entity != "player" else 0.0
        return dx * push + jitter, dy * push

    def draw(self, entities: dict, view, now: float) -> None:
        if view is None:
            self.tracks.clear()
            return
        grid, overlay = self.grid, self.grid.overlay
        cw, ch = grid.cell_size()
        tracks = {}
        for entity, (sx, sy, sprite, tint) in entities.items():
            wx, wy = view.x + sx, view.y + sy
            track = self.tracks.get(entity)
            if track is None or max(abs(wx - track[2]), abs(wy - track[3])) > 1:
                track = [wx, wy, wx, wy, now, TWEEN_MAX, 1]
            elif (wx, wy) != (track[2], track[3]):
                x, y = _glide(track, now)
                gap = min(max(now - track[4], TWEEN_MIN), TWEEN_MAX)
                heading = track[6] if wx == track[2] else (1 if wx > track[2] else -1)
                track = [x, y, wx, wy, now, gap, heading]
            tracks[entity] = track
            x, y = _glide(track, now)
            nx, ny = self._nudge(entity, now)
            x, y = x + nx, y + ny
            phase = hash(entity) % 7
            # Moving (still gliding, or stepped a moment ago): walk cycle; else idle.
            walking = now - track[4] < track[5] + 0.1
            step = walk_frame(sprite, now, phase) if walking else None
            frame, mirrored = step if step else (frame_at(sprite, now, phase), False)
            if facing(sprite) * track[6] < 0:
                mirrored = not mirrored
            texture = _sprite_texture(sprite, frame)
            if texture is None:
                continue
            overlay.add(Color(*_rgba(tint or _WHITE)[:3], 1))
            pos = (grid.x + (x - view.x) * cw + grid.scroll.x,
                   grid.top - (y - view.y + 1) * ch + grid.scroll.y)  # fmt: skip
            coords = _MIRRORED if mirrored else _UPRIGHT
            overlay.add(Rectangle(texture=texture, pos=pos, size=(cw, ch), tex_coords=coords))
        self.tracks = tracks


_UPRIGHT = (0, 0, 1, 0, 1, 1, 0, 1)
_MIRRORED = (1, 0, 0, 0, 0, 1, 1, 1)  # left-right flip


def _glide(track, now: float) -> tuple:
    """Where a track's thing is drawn now (world tiles, fractional)."""
    from_x, from_y, to_x, to_y, start, duration = track[:6]
    t = min(1.0, (now - start) / duration)
    return from_x + (to_x - from_x) * t, from_y + (to_y - from_y) * t


class RainLayer:
    """Rain over the world: thin streaks falling with a little wind, and small splashes
    flickering on the ground. Screen-space and stateless: positions come from time."""

    STREAKS = 110
    SPLASHES = 40

    def __init__(self, grid: GridView):
        self.grid = grid
        rng = random.Random(7)
        self._streaks = [
            (rng.random(), rng.random(), rng.uniform(0.8, 1.2)) for _ in range(self.STREAKS)
        ]
        self._splashes = [(rng.random(), rng.random(), rng.random()) for _ in range(self.SPLASHES)]

    def draw(self, raining: bool, now: float) -> None:
        if not raining:
            return
        grid, overlay = self.grid, self.grid.overlay
        cw, ch = grid.cell_size()
        left, width = grid.x, grid.width
        height = WORLD_ROWS * ch
        bottom = grid.top - height
        overlay.add(Color(0.75, 0.85, 1.0, 0.45))
        for x0, y0, speed in self._streaks:
            fall = (y0 + now * 1.6 * speed) % 1.0  # screens per second
            y = grid.top - fall * height
            x = left + ((x0 - fall * 0.08) % 1.0) * width  # wind: drift left as it falls
            overlay.add(Rectangle(pos=(round(x), round(y)), size=(max(1, round(cw / 8)), ch * 0.6)))
        overlay.add(Color(0.85, 0.92, 1.0, 0.6))
        for x0, y0, phase in self._splashes:
            if (now * 3 + phase) % 1.0 < 0.25:  # each splash shows for a moment
                pos = (round(left + x0 * width), round(bottom + y0 * height))
                overlay.add(Rectangle(pos=pos, size=(round(cw / 3), max(1, round(cw / 8)))))


class ParticleLayer:
    """Draws mobile/particles.py bursts as small square pixels over the world."""

    def __init__(self, grid: GridView):
        self.grid = grid
        self.particles: list = []
        self._rng = random.Random()  # visual only: never the game's RNG
        self._last = None

    def add(self, events) -> None:
        for event in events:
            color = event.color or event.text_color
            self.particles += burst(event.kind, event.x, event.y, color, self._rng)

    def draw(self, view, now: float) -> None:
        dt = 0.0 if self._last is None else min(now - self._last, 0.1)
        self._last = now
        self.particles = step(self.particles, dt)
        if view is None:
            return
        grid, overlay = self.grid, self.grid.overlay
        cw, ch = grid.cell_size()
        for p in self.particles:
            if not view.contains(p.wx, p.wy):
                continue
            size = max(2.0, round(p.size * cw))  # whole pixels keep the pixel-art look
            x = grid.x + (p.wx - view.x + 0.5) * cw + p.ox * cw + grid.scroll.x
            y = grid.top - (p.wy - view.y + 0.5) * ch + p.oy * cw + grid.scroll.y
            overlay.add(Color(*_rgba(p.color)[:3], p.alpha))
            corner = (round(x - size / 2), round(y - size / 2))
            overlay.add(Rectangle(pos=corner, size=(size, size)))


class SoundEffects:
    """Plays the synthesized effect of each event kind (mobile/sfx.py) and a short
    vibration for the important ones; both can be turned off together."""

    def __init__(self, folder: str, enabled: bool):
        self.enabled = enabled
        self.vibrator = _android_vibrator()
        self.sounds = {}
        for kind, path in write_sounds(folder).items():
            sound = SoundLoader.load(path)
            if sound is not None:  # no audio backend: stay silent
                self.sounds[kind] = sound

    def tap(self) -> None:
        """The short click of a touch button."""
        sound = self.sounds.get("tap")
        if self.enabled and sound is not None:
            sound.stop()
            sound.play()

    def play(self, events) -> None:
        if not self.enabled:
            return
        kinds = {event.kind for event in events}
        for kind in kinds:
            sound = self.sounds.get(kind)
            if sound is not None:
                sound.stop()  # restart if it is still playing
                sound.play()
        buzz = max((VIBRATE_MS.get(kind, 0) for kind in kinds), default=0)
        if buzz and self.vibrator is not None:
            self.vibrator.vibrate(buzz)


AMBIENCE_VOLUME = 0.35


class Ambience:
    """Background sound: a looping bed for the place (rain, breeze or the cave's hum)
    with one-shots scattered over it at irregular times and distances (volumes):
    birdsong by day, crickets at night, drips underground. Silent outside the world."""

    def __init__(self, sfx: "SoundEffects"):
        self.sfx = sfx
        self.bed = None
        self.next_call = 0.0
        self._rng = random.Random()

    def _set_bed(self, name) -> None:
        if name == self.bed:
            return
        for sound_name in (self.bed, name):
            sound = self.sfx.sounds.get(sound_name) if sound_name else None
            if sound is not None and sound_name == self.bed:
                sound.stop()
            elif sound is not None:
                sound.loop = True
                sound.volume = AMBIENCE_VOLUME
                sound.play()
        self.bed = name

    def update(self, state, in_world: bool, now: float) -> None:
        if not (in_world and self.sfx.enabled):
            self._set_bed(None)
            return
        underground = biome_at(state.player_x, state.player_y) == "cave"
        raining = weather.rain_here(state)
        self._set_bed("cave" if underground else "rain" if raining else "breeze")
        if now < self.next_call:
            return
        self.next_call = now + self._rng.uniform(1.5, 6.0)
        night = daylight.phase(state)[0] == "night"
        call = "drip" if underground else None if raining else "cricket" if night else "chirp"
        sound = self.sfx.sounds.get(call) if call else None
        if sound is not None:
            sound.volume = self._rng.uniform(0.15, 0.5)  # near or far
            sound.stop()
            sound.play()


class GemCollectorApp(App):
    title = "Gem Collector"

    def build(self):
        # Saves and the profile live in the app's private storage on Android.
        os.environ.setdefault(persistence.DATA_DIR_ENV, self.user_data_dir)
        set_hints(TOUCH_HINTS)
        self.state = GameState(active_scene="menu")
        self.scenes = SceneManager(build_scenes())
        self.renderer = GridRenderer()
        self.touch = TouchController()
        self.keys: set = set()
        # Frontend preferences (not part of the game's save).
        self.settings = JsonStore(os.path.join(self.user_data_dir, "settings.json"))
        sound_on = self.settings.get("sound")["on"] if self.settings.exists("sound") else True
        self.sfx = SoundEffects(os.path.join(self.user_data_dir, "sfx"), sound_on)
        self.ambience = Ambience(self.sfx)

        root = BoxLayout(orientation="horizontal")
        self.grid = GridView(tap_handler=self._tap_cell, size_hint=(0.74, 1))
        root.add_widget(self.grid)
        self.floats = FloatingTexts(self.grid)
        self.particles = ParticleLayer(self.grid)
        self.entity_layer = EntityLayer(self.grid)
        self.rain = RainLayer(self.grid)
        self.shake = ScreenShake(self.grid)
        self.slide = WorldSlide(self.grid)
        root.add_widget(self._controls())
        Window.bind(on_key_down=self._key_down)
        Clock.schedule_interval(self._frame, 1 / FPS)
        return root

    # ── Controls ──────────────────────────────────────────────────────────────

    def _controls(self):
        panel = BoxLayout(orientation="vertical", size_hint=(0.26, 1), padding=dp(6), spacing=dp(6))
        # 5 rows of actions above 3 rows of d-pad: rows share the height evenly, so the
        # panel fits short landscape screens (360 dp gives ~40 dp per row).
        actions = GridLayout(cols=2, spacing=dp(6), size_hint_y=5 / 8)
        for label, action in [("Use", Action.USE), ("Attack", Action.ATTACK),
                              ("Tool", Action.CYCLE_TOOL), ("Recall", Action.RECALL),
                              ("OK", Action.CONFIRM), ("Back", Action.CANCEL),
                              ("Tab", Action.NEXT_TAB), ("Item", Action.USE_ITEM),
                              ("Map", Action.MAP)]:  # fmt: skip
            button = Button(text=label)
            button.bind(on_press=lambda _b, a=action: self.touch.press(a))
            button.bind(on_press=lambda _b: self.sfx.tap())
            actions.add_widget(button)
        self.sound_button = Button(text=self._sound_label())
        self.sound_button.bind(on_press=lambda _b: self._toggle_sound())
        actions.add_widget(self.sound_button)
        pad = GridLayout(cols=3, spacing=dp(6), size_hint_y=3 / 8)
        for label, action in [("", None), ("^", Action.MOVE_UP), ("", None),
                              ("<", Action.MOVE_LEFT), ("", None), (">", Action.MOVE_RIGHT),
                              ("", None), ("v", Action.MOVE_DOWN), ("", None)]:  # fmt: skip
            if action is None:
                pad.add_widget(Widget())
                continue
            # always_release: lifting the finger anywhere (even after sliding off the
            # button) ends the hold, so the player never keeps walking on their own.
            button = Button(text=label, font_size=dp(22), always_release=True)
            # A d-pad tap moves one step (and navigates menus); holding keeps moving.
            button.bind(on_press=lambda _b, a=action: self._dpad_down(a))
            button.bind(on_press=lambda _b: self.sfx.tap())
            button.bind(on_release=lambda _b, a=action: self.touch.hold(a, False))
            pad.add_widget(button)
        panel.add_widget(actions)
        panel.add_widget(pad)
        return panel

    def _sound_label(self):
        return "Sound/Vib: on" if self.sfx.enabled else "Sound/Vib: off"

    def _toggle_sound(self):
        self.sfx.enabled = not self.sfx.enabled
        self.settings.put("sound", on=self.sfx.enabled)
        self.sound_button.text = self._sound_label()

    def _dpad_down(self, action):
        self.touch.press(action)
        self.touch.hold(action, True)

    def _tap_cell(self, x, y):
        state = self.state
        if state.active_scene != "game" or y >= ROWS - HUD_ROWS:
            return
        view = camera.render_view(state, self.renderer)
        if 0 <= x < view.width and 0 <= y < view.height:
            self.touch.tap_world(state, view.x + x, view.y + y)

    def _key_down(self, _window, key, _scancode, codepoint, _modifiers):
        name = _KEY_NAMES.get(key) or (codepoint.lower() if codepoint else None)
        if name:
            self.keys.add(name)
        return True  # keep Esc/back inside the game

    # ── Frame loop and lifecycle ──────────────────────────────────────────────

    def _frame(self, dt):
        touch_inp = self.touch.poll(self.state)
        key_inp = map_keys(self.keys)
        self.keys.clear()
        inp = InputState(pressed=touch_inp.pressed | key_inp.pressed, held=touch_inp.held)
        self.scenes.frame(inp, self.state, dt, self.renderer)
        self.grid.flush(self.renderer)
        now = time.perf_counter()
        events = take_events(self.state)
        self.floats.add(events, now)
        self.particles.add(events)
        self.entity_layer.react(events, now)
        self.sfx.play(events)
        self.shake.update(events, now)
        in_world = self.state.active_scene == "game"
        view = camera.render_view(self.state, self.renderer) if in_world else None
        self.slide.update(view, now)
        self.grid.overlay.clear()
        entities, self.renderer.entities = self.renderer.entities, {}
        self.entity_layer.draw(entities, view, now)
        self.particles.draw(view, now)  # under the texts
        self.rain.draw(view is not None and weather.rain_here(self.state), now)
        self.ambience.update(self.state, view is not None, now)
        self.floats.draw(view, now)
        if self.state.quit_requested:
            self.stop()

    def on_pause(self):
        self.ambience.update(self.state, False, 0.0)
        # Android may kill a paused app: keep a run that is being played.
        if persistence.autosave_allowed(self.state):
            persistence.save_game(self.state)
        self.touch.release_all()
        return True

    def on_resume(self):
        # Time spent in the background must not be simulated.
        self.scenes.scenes["game"].timestep.reset()


if __name__ == "__main__":
    GemCollectorApp().run()
