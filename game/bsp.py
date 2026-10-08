import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BSPNode:
    x: int
    y: int
    width: int
    height: int
    left: Optional["BSPNode"] = field(default=None, repr=False)
    right: Optional["BSPNode"] = field(default=None, repr=False)
    room_x: int | None = None
    room_y: int | None = None
    room_w: int | None = None
    room_h: int | None = None


def split(node: BSPNode, rng: random.Random, min_size: int = 8) -> None:
    if node.width > node.height * 1.25:
        split_horizontal = False
    elif node.height > node.width * 1.25:
        split_horizontal = True
    else:
        split_horizontal = rng.choice([True, False])

    if split_horizontal:
        if node.height < 2 * min_size:
            return
        split_y = rng.randint(min_size, node.height - min_size)
        node.left = BSPNode(x=node.x, y=node.y, width=node.width, height=split_y)
        node.right = BSPNode(
            x=node.x,
            y=node.y + split_y,
            width=node.width,
            height=node.height - split_y,
        )
    else:
        if node.width < 2 * min_size:
            return
        split_x = rng.randint(min_size, node.width - min_size)
        node.left = BSPNode(x=node.x, y=node.y, width=split_x, height=node.height)
        node.right = BSPNode(
            x=node.x + split_x,
            y=node.y,
            width=node.width - split_x,
            height=node.height,
        )

    split(node.left, rng, min_size)
    split(node.right, rng, min_size)


def get_leaves(node: BSPNode) -> list[BSPNode]:
    if node.left is None and node.right is None:
        return [node]
    leaves: list[BSPNode] = []
    if node.left is not None:
        leaves.extend(get_leaves(node.left))
    if node.right is not None:
        leaves.extend(get_leaves(node.right))
    return leaves


def place_rooms(node: BSPNode, rng: random.Random, margin: int = 1) -> None:
    for leaf in get_leaves(node):
        if leaf.width < 2 * margin + 4 or leaf.height < 2 * margin + 4:
            continue
        max_w = leaf.width - 2 * margin
        max_h = leaf.height - 2 * margin
        min_w = max(4, leaf.width // 2)
        min_h = max(4, leaf.height // 2)
        if min_w > max_w:
            min_w = max_w
        if min_h > max_h:
            min_h = max_h
        room_w = rng.randint(min_w, max_w)
        room_h = rng.randint(min_h, max_h)
        room_x = leaf.x + margin + rng.randint(0, max_w - room_w)
        room_y = leaf.y + margin + rng.randint(0, max_h - room_h)
        leaf.room_x = room_x
        leaf.room_y = room_y
        leaf.room_w = room_w
        leaf.room_h = room_h


def _get_room_center(node: BSPNode) -> tuple[int, int] | None:
    if node.left is None and node.right is None:
        if node.room_x is None:
            return None
        return (node.room_x + node.room_w // 2, node.room_y + node.room_h // 2)

    left_center = _get_room_center(node.left) if node.left is not None else None
    right_center = _get_room_center(node.right) if node.right is not None else None

    if left_center is not None and right_center is not None:
        return (
            (left_center[0] + right_center[0]) // 2,
            (left_center[1] + right_center[1]) // 2,
        )
    return left_center if left_center is not None else right_center


def connect_rooms(node: BSPNode) -> list[tuple[int, int, int, int]]:
    corridors: list[tuple[int, int, int, int]] = []

    if node.left is None or node.right is None:
        return corridors

    corridors.extend(connect_rooms(node.left))
    corridors.extend(connect_rooms(node.right))

    left_center = _get_room_center(node.left)
    right_center = _get_room_center(node.right)

    if left_center is None or right_center is None:
        return corridors

    x1, y1 = left_center
    x2, y2 = right_center
    corridors.append((x1, y1, x2, y2))

    return corridors
