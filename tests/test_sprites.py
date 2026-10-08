import importlib.util
import pathlib

from clingine.renderer import StubRenderer
from game import camera
from game.constants import TILE_PROPS
from game.decor import DECOR_NAMES
from game.enemies import HIT_TINT, Enemy
from game.objects.registry import CRITTERS, ENEMY_CATALOG
from game.scenes.game import GameScene
from game.simulation import new_run

_SPEC = importlib.util.spec_from_file_location(
    "sprites", pathlib.Path(__file__).parent.parent / "mobile" / "sprites.py"
)
sprites = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sprites)


class SpriteRecorder(StubRenderer):
    def __init__(self, width, height):
        super().__init__(width, height)
        self.sprites = {}
        self.entities = {}

    def set_sprite(self, x, y, layer, sprite, tint, entity=None):
        self.sprites[(x, y, layer)] = (sprite, tint)
        if entity is not None:
            self.entities[entity] = (x, y, sprite)


def test_every_sprite_the_game_draws_has_pixel_art():
    needed = set(TILE_PROPS) | {"depleted", "player", "gem", "bag"} | set(ENEMY_CATALOG)
    needed |= set(DECOR_NAMES)
    needed |= set(CRITTERS)
    assert needed <= set(sprites.SPRITES)


def test_sprites_and_their_frames_are_well_formed():
    for sprite_id in sprites.SPRITES:
        for frame in range(sprites.frame_count(sprite_id)):
            rows = sprites.sprite_rows(sprite_id, frame)
            assert len(rows) == sprites.HEIGHT, (sprite_id, frame)
            assert all(len(row) == sprites.WIDTH for row in rows), (sprite_id, frame)
            assert all(letter in sprites.PALETTE for row in rows for letter in row)
            pixels = sprites.sprite_rgba(sprite_id, frame)
            assert len(pixels) == sprites.WIDTH * sprites.HEIGHT * 4


def test_animated_sprites_cycle_through_their_frames():
    assert set(sprites.FPS) == set(sprites.FRAMES) <= set(sprites.SPRITES)
    for sprite_id in sprites.FRAMES:
        count, fps = sprites.frame_count(sprite_id), sprites.FPS[sprite_id]
        seen = [sprites.frame_at(sprite_id, i / fps) for i in range(count)]
        assert seen == list(range(count)), sprite_id
        assert sprites.frame_at(sprite_id, 0, phase=1) == 1
        assert sprites.sprite_rgba(sprite_id, 1) != sprites.sprite_rgba(sprite_id, 0)
    assert sprites.frame_at("grass", 123.4, phase=5) == 0  # still sprites never move


def test_rgba_starts_at_the_bottom_row_and_keeps_transparency():
    pixels = sprites.sprite_rgba("player")
    assert pixels[:4] == bytes(4)  # bottom-left pixel of "player" is transparent
    assert sprites.sprite_rgba("no_such_sprite") is None


def test_game_scene_sets_ground_and_object_sprites():
    state = new_run(6)
    state.enemies = []
    renderer = SpriteRecorder(80, 24)
    GameScene().render(renderer, state)
    view = camera.render_view(state, renderer)
    px, py = state.player_x - view.x, state.player_y - view.y
    assert renderer.sprites[(px, py, camera.OBJECT)] == ("player", None)
    ground_type = state.world_tiles.meta[(state.player_x, state.player_y)]["type"]
    assert renderer.sprites[(px, py, camera.GROUND)] == (ground_type, None)
    for sx, sy, _layer in renderer.sprites:
        tile = state.world_tiles.meta[(view.x + sx, view.y + sy)]
        assert tile["visibility"] != "unseen"


def test_explored_ground_is_dimmed_and_hit_enemies_tinted():
    state = new_run(6)
    renderer = SpriteRecorder(80, 24)
    view = camera.render_view(state, renderer)
    pos = (view.x, view.y)
    state.world_tiles.meta[pos]["visibility"] = "explored"
    enemy = Enemy(state.player_x + 1, state.player_y, "snake")
    enemy.flash_timer = 0.2
    state.enemies = [enemy]
    GameScene().render(renderer, state)
    assert renderer.sprites[(0, 0, camera.GROUND)][1] == camera.EXPLORED_TINT
    ex, ey = enemy.x - view.x, enemy.y - view.y
    assert renderer.sprites[(ex, ey, camera.OBJECT)] == ("snake", HIT_TINT)
    # Moving things carry a stable key so a frontend can glide them between cells.
    assert renderer.entities[id(enemy)] == (ex, ey, "snake")
    assert renderer.entities["player"][2] == "player"
