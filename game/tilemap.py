class TileMap:
    """The world grid as data: per-tile gameplay state keyed by (x, y).

    ``meta[(x, y)]`` holds {"type", "walkable", "interactable", "depleted", "visibility"}.
    Nothing here describes appearance; see game/theme.py.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.meta: dict = {}
        self.start_pos: tuple | None = None
