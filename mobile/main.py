"""Gem Collector: Kivy frontend (Android, also runs on the desktop for testing).

The game itself is the same package the terminal version uses. This file only:
draws the 80x24 cell grid with Kivy (pixel-art sprites from sprites.py where the game
sets them, characters elsewhere), turns touches/buttons/keys into InputState
(game/touch.py), and handles the Android lifecycle (save on pause, back button).

Desktop:  .venv-mobile/bin/python mobile/main.py
Android:  see docs/ANDROID.md
"""

import os
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
from kivy.graphics import Color, Rectangle  # noqa: E402
from kivy.graphics.texture import Texture  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.storage.jsonstore import JsonStore  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402
from kivy.uix.button import Button  # noqa: E402
from kivy.uix.gridlayout import GridLayout  # noqa: E402
from kivy.uix.widget import Widget  # noqa: E402
from sfx import write_sounds  # noqa: E402
from sprites import HEIGHT as SPRITE_HEIGHT  # noqa: E402
from sprites import WIDTH as SPRITE_WIDTH  # noqa: E402
from sprites import sprite_rgba  # noqa: E402

from clingine.renderer import Renderer  # noqa: E402
from game import camera, persistence  # noqa: E402
from game.constants import FPS, HUD_ROWS  # noqa: E402
from game.events import take_events  # noqa: E402
from game.input import Action, InputState, map_keys, set_hints  # noqa: E402
from game.scenes import SceneManager, build_scenes  # noqa: E402
from game.state import GameState  # noqa: E402
from game.theme import ASCII_FALLBACK  # noqa: E402
from game.touch import TouchController  # noqa: E402

COLS, ROWS = 80, 24
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

    def set_sprite(self, x, y, layer, sprite, tint):
        if 0 <= x < COLS and 0 <= y < ROWS:
            self.sprites.setdefault((x, y), {})[layer] = (sprite, tint)


def _rgba(rgb):
    return (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1)


_WHITE = (255, 255, 255)
_textures: dict = {}


def _sprite_texture(sprite):
    """The sprite's texture (built once, scaled without smoothing), or None."""
    if sprite not in _textures:
        pixels = sprite_rgba(sprite)
        texture = None
        if pixels is not None:
            texture = Texture.create(size=(SPRITE_WIDTH, SPRITE_HEIGHT), colorfmt="rgba")
            texture.blit_buffer(pixels, colorfmt="rgba", bufferfmt="ubyte")
            texture.mag_filter = texture.min_filter = "nearest"
        _textures[sprite] = texture
    return _textures[sprite]


class GridView(Widget):
    """Draws a GridRenderer: per cell, a background rectangle (solid color or ground
    sprite) and a foreground one (glyph or object sprite)."""

    def __init__(self, tap_handler, **kwargs):
        super().__init__(**kwargs)
        self.tap_handler = tap_handler
        self._glyphs: dict = {}
        self._bg, self._fg = [], []
        with self.canvas:
            for _ in range(ROWS * COLS):
                self._bg.append((Color(0, 0, 0, 1), Rectangle()))
                self._fg.append((Color(1, 1, 1, 1), Rectangle()))
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
        """(texture, tint) for a (sprite, tint) layer, or None if it has no sprite."""
        if layer is None:
            return None
        texture = _sprite_texture(layer[0])
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
        canvas = self.grid.canvas.after
        canvas.clear()
        self.items = [item for item in self.items if now - item[1] < FLOAT_SECONDS]
        if view is None:
            return
        grid = self.grid
        cw, ch = grid.cell_size()
        with canvas:
            for event, born, slot in self.items:
                if not view.contains(event.x, event.y):
                    continue
                age = (now - born) / FLOAT_SECONDS
                alpha = 1.0 if age < 0.6 else (1.0 - age) / 0.4
                label = self._label(event.text, max(ch * 0.8, 8))
                icon = _sprite_texture(event.icon) if event.icon else None
                icon_w = cw * 1.4 if icon else 0
                width = icon_w + label.width
                center_x = grid.x + (event.x - view.x + 0.5) * cw
                left = min(max(center_x - width / 2, grid.x), grid.right - width)
                bottom = grid.top - (event.y - view.y) * ch + (slot + age * FLOAT_RISE) * ch
                if icon:
                    Color(*_rgba(event.color or _WHITE)[:3], alpha)
                    Rectangle(texture=icon, pos=(left, bottom), size=(icon_w, ch * 1.4))
                Color(*_rgba(event.text_color)[:3], alpha)
                text_y = bottom + (ch * 1.4 - label.height) / 2
                Rectangle(texture=label, pos=(left + icon_w, text_y), size=label.size)


class SoundEffects:
    """Plays the synthesized effect of each event kind (mobile/sfx.py); can be muted."""

    def __init__(self, folder: str, enabled: bool):
        self.enabled = enabled
        self.sounds = {}
        for kind, path in write_sounds(folder).items():
            sound = SoundLoader.load(path)
            if sound is not None:  # no audio backend: stay silent
                self.sounds[kind] = sound

    def play(self, events) -> None:
        if not self.enabled:
            return
        for kind in {event.kind for event in events}:
            sound = self.sounds.get(kind)
            if sound is not None:
                sound.stop()  # restart if it is still playing
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

        root = BoxLayout(orientation="horizontal")
        self.grid = GridView(tap_handler=self._tap_cell, size_hint=(0.74, 1))
        root.add_widget(self.grid)
        self.floats = FloatingTexts(self.grid)
        root.add_widget(self._controls())
        Window.bind(on_key_down=self._key_down)
        Clock.schedule_interval(self._frame, 1 / FPS)
        return root

    # ── Controls ──────────────────────────────────────────────────────────────

    def _controls(self):
        panel = BoxLayout(orientation="vertical", size_hint=(0.26, 1), padding=dp(6), spacing=dp(6))
        # 4 rows of actions above 3 rows of d-pad: rows share the height evenly, so the
        # panel fits short landscape screens (360 dp gives ~44 dp per row).
        actions = GridLayout(cols=2, spacing=dp(6), size_hint_y=4 / 7)
        for label, action in [("Use", Action.USE), ("Attack", Action.ATTACK),
                              ("Tool", Action.CYCLE_TOOL), ("Recall", Action.RECALL),
                              ("OK", Action.CONFIRM), ("Back", Action.CANCEL),
                              ("Tab", Action.NEXT_TAB)]:  # fmt: skip
            button = Button(text=label)
            button.bind(on_press=lambda _b, a=action: self.touch.press(a))
            actions.add_widget(button)
        self.sound_button = Button(text=self._sound_label())
        self.sound_button.bind(on_press=lambda _b: self._toggle_sound())
        actions.add_widget(self.sound_button)
        pad = GridLayout(cols=3, spacing=dp(6), size_hint_y=3 / 7)
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
            button.bind(on_release=lambda _b, a=action: self.touch.hold(a, False))
            pad.add_widget(button)
        panel.add_widget(actions)
        panel.add_widget(pad)
        return panel

    def _sound_label(self):
        return "Sound: on" if self.sfx.enabled else "Sound: off"

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
        self.sfx.play(events)
        in_world = self.state.active_scene == "game"
        self.floats.draw(camera.render_view(self.state, self.renderer) if in_world else None, now)
        if self.state.quit_requested:
            self.stop()

    def on_pause(self):
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
