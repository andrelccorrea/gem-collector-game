from game import landmarks
from game.geography import biome_at
from game.persistence import load_game, save_game
from game.simulation import new_run
from game.tile_info import describe_here


def test_landmarks_are_placed_by_the_seed_on_their_ground_and_spread_out():
    state = new_run(21)
    placed = landmarks.landmarks(state)
    assert placed == landmarks._place(state)  # same seed, same places
    assert 8 <= len(placed) <= sum(entry[3] for entry in landmarks.LANDMARKS.values())
    for (x, y), kind in placed.items():
        _, ground, biome, *_ = landmarks.LANDMARKS[kind]
        assert state.world_tiles.meta[(x, y)]["type"] == ground and biome_at(x, y) == biome
    positions = list(placed)
    for i, (ax, ay) in enumerate(positions):
        for bx, by in positions[i + 1 :]:
            assert max(abs(ax - bx), abs(ay - by)) >= landmarks.SPACING


def test_a_first_visit_tells_the_story_and_pays_once_per_run():
    state = new_run(21)
    (x, y), kind = next(
        (pos, k) for pos, k in landmarks.landmarks(state).items() if landmarks.LANDMARKS[k][4]
    )
    name, *_, gold, lore = landmarks.LANDMARKS[kind]
    state.player_x, state.player_y = x, y
    before = state.player_gold
    landmarks.visit(state)
    assert state.player_gold == before + gold
    assert state.hud_message.startswith(f"{name}: {lore}")
    landmarks.visit(state)
    assert state.player_gold == before + gold  # once
    assert name.lower() in describe_here(state)
    assert save_game(state) is None
    assert (x, y) in load_game().visited_landmarks
