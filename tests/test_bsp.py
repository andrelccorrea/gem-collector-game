import random

from game.bsp import BSPNode, connect_rooms, get_leaves, place_rooms, split

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_node(w: int, h: int, x: int = 0, y: int = 0) -> BSPNode:
    return BSPNode(x=x, y=y, width=w, height=h)


def _collect_leaves(node: BSPNode) -> list[BSPNode]:
    return get_leaves(node)


# ---------------------------------------------------------------------------
# test_bsp_split_creates_children
# ---------------------------------------------------------------------------


def test_bsp_split_creates_children():
    """split() on a large-enough node must create non-None left and right children."""
    node = _make_node(40, 40)
    rng = random.Random(7)
    split(node, rng, min_size=8)

    assert node.left is not None, "left child should have been created"
    assert node.right is not None, "right child should have been created"


# ---------------------------------------------------------------------------
# test_bsp_split_deterministic
# ---------------------------------------------------------------------------


def test_bsp_split_deterministic():
    """Calling split with the same RNG seed on identical nodes yields identical leaves."""
    node_a = _make_node(40, 40)
    node_b = _make_node(40, 40)

    split(node_a, random.Random(42), min_size=8)
    split(node_b, random.Random(42), min_size=8)

    leaves_a = [(n.x, n.y, n.width, n.height) for n in get_leaves(node_a)]
    leaves_b = [(n.x, n.y, n.width, n.height) for n in get_leaves(node_b)]

    assert leaves_a == leaves_b, "Leaves must be identical when using the same RNG seed"


# ---------------------------------------------------------------------------
# test_bsp_leaves_cover_area
# ---------------------------------------------------------------------------


def test_bsp_leaves_cover_area():
    """Total area of all leaves should equal the original node's area (60×60 = 3600)."""
    node = _make_node(60, 60)
    rng = random.Random(1)
    split(node, rng, min_size=8)

    leaves = get_leaves(node)
    total_area = sum(leaf.width * leaf.height for leaf in leaves)

    assert total_area == 60 * 60, f"Expected area 3600, got {total_area}"


# ---------------------------------------------------------------------------
# test_bsp_min_size_respected
# ---------------------------------------------------------------------------


def test_bsp_min_size_respected():
    """After splitting a 40×40 node with min_size=8, no leaf should be smaller than 8×8."""
    node = _make_node(40, 40)
    rng = random.Random(99)
    split(node, rng, min_size=8)

    for leaf in get_leaves(node):
        assert leaf.width >= 8, f"Leaf width {leaf.width} < min_size 8"
        assert leaf.height >= 8, f"Leaf height {leaf.height} < min_size 8"


# ---------------------------------------------------------------------------
# test_bsp_leaves_no_children
# ---------------------------------------------------------------------------


def test_bsp_leaves_no_children():
    """Every node returned by get_leaves() must be a leaf (no children)."""
    node = _make_node(60, 60)
    rng = random.Random(5)
    split(node, rng, min_size=8)

    for leaf in get_leaves(node):
        assert leaf.left is None, "Leaf should have left=None"
        assert leaf.right is None, "Leaf should have right=None"


# ---------------------------------------------------------------------------
# test_bsp_place_rooms_sets_room_on_leaves
# ---------------------------------------------------------------------------


def test_bsp_place_rooms_sets_room_on_leaves():
    """place_rooms() should assign a room to at least one leaf."""
    node = _make_node(60, 60)
    rng = random.Random(3)
    split(node, rng, min_size=8)
    place_rooms(node, rng)

    leaves_with_room = [leaf for leaf in get_leaves(node) if leaf.room_x is not None]
    assert len(leaves_with_room) >= 1, "At least one leaf should have a room placed"


# ---------------------------------------------------------------------------
# test_bsp_place_rooms_rooms_fit_in_partition
# ---------------------------------------------------------------------------


def test_bsp_place_rooms_rooms_fit_in_partition():
    """All placed rooms must fit within their leaf partition (respecting margin=1)."""
    node = _make_node(80, 80)
    rng = random.Random(17)
    split(node, rng, min_size=8)
    place_rooms(node, rng, margin=1)

    margin = 1
    for leaf in get_leaves(node):
        if leaf.room_x is None:
            continue  # leaf was too small, correctly skipped
        assert (
            leaf.room_x >= leaf.x + margin
        ), f"room_x {leaf.room_x} < leaf.x+margin {leaf.x + margin}"
        assert (
            leaf.room_y >= leaf.y + margin
        ), f"room_y {leaf.room_y} < leaf.y+margin {leaf.y + margin}"
        assert leaf.room_x + leaf.room_w <= leaf.x + leaf.width - margin, (
            f"room right edge {leaf.room_x + leaf.room_w} "
            f"> leaf right inner edge {leaf.x + leaf.width - margin}"
        )
        assert leaf.room_y + leaf.room_h <= leaf.y + leaf.height - margin, (
            f"room bottom edge {leaf.room_y + leaf.room_h} "
            f"> leaf bottom inner edge {leaf.y + leaf.height - margin}"
        )


# ---------------------------------------------------------------------------
# test_bsp_connect_rooms_returns_segments
# ---------------------------------------------------------------------------


def test_bsp_connect_rooms_returns_segments():
    """connect_rooms() must return a list of 4-integer tuples."""
    node = _make_node(60, 60)
    rng = random.Random(55)
    split(node, rng, min_size=8)
    place_rooms(node, rng)

    corridors = connect_rooms(node)

    assert isinstance(corridors, list), "connect_rooms should return a list"
    for segment in corridors:
        assert len(segment) == 4, f"Each corridor segment must have 4 values, got {len(segment)}"
        for val in segment:
            assert isinstance(val, int), f"Corridor value {val!r} is not an int"


# ---------------------------------------------------------------------------
# test_bsp_single_node_no_split
# ---------------------------------------------------------------------------


def test_bsp_single_node_no_split():
    """A node smaller than 2*min_size should not be split; get_leaves() returns it alone."""
    node = _make_node(6, 6)
    rng = random.Random(0)
    split(node, rng, min_size=8)

    assert node.left is None, "Tiny node should have no left child after split attempt"
    assert node.right is None, "Tiny node should have no right child after split attempt"

    leaves = get_leaves(node)
    assert len(leaves) == 1, f"Expected 1 leaf for unsplit node, got {len(leaves)}"
    assert leaves[0] is node, "The single leaf must be the original node itself"
