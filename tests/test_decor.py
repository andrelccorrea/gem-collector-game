from collections import Counter

from game.decor import DECOR, DECOR_NAMES, decoration
from game.landmarks import LANDMARKS
from game.simulation import new_run
from game.theme import ASCII_FALLBACK, DECOR_APPEARANCE


def test_decorations_are_stable_and_only_on_their_ground():
    state = new_run(8)
    meta = state.world_tiles.meta
    first = {pos: decoration(8, *pos, tile) for pos, tile in meta.items()}
    assert first == {pos: decoration(8, *pos, tile) for pos, tile in meta.items()}
    for pos, deco in first.items():
        if deco is not None:
            assert deco in [name for name, *_ in DECOR[meta[pos]["type"]]]


def test_decorations_are_sparse_and_vary_with_the_seed():
    state = new_run(8)
    counts = Counter(decoration(8, *p, t) for p, t in state.world_tiles.meta.items())
    decorated = sum(n for deco, n in counts.items() if deco)
    assert 0.01 < decorated / sum(counts.values()) < 0.15
    other = [decoration(9, *p, t) for p, t in state.world_tiles.meta.items()]
    assert other != [decoration(8, *p, t) for p, t in state.world_tiles.meta.items()]


def test_worked_out_ground_is_bare():
    assert decoration(1, 0, 0, {"type": "grass", "depleted": True}) is None


def test_every_decoration_has_a_name_and_a_terminal_look():
    names = {name for options in DECOR.values() for name, *_ in options}
    assert names == set(DECOR_NAMES)
    assert set(DECOR_APPEARANCE) == names | set(LANDMARKS)  # landmarks are drawn the same way
    for char, _ in DECOR_APPEARANCE.values():
        assert char.isascii() or char in ASCII_FALLBACK
