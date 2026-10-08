import math


class Surface:
    def __init__(self, width: int, height: int, default_char: str = " ", default_color_pair=None):
        self.width = width
        self.height = height
        self.default_char = default_char
        self.default_color_pair = default_color_pair
        # tiles[y][x] = [char, color_pair]
        self.tiles = [
            [[default_char, default_color_pair] for _ in range(width)] for _ in range(height)
        ]
        self.meta: dict = {}
        self.start_pos: tuple | None = None

    def set_tile(self, x: int, y: int, char: str, color_pair=None) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = [char, color_pair]

    def get_tile(self, x: int, y: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return None

    def fill(self, char: str, color_pair=None) -> None:
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x] = [char, color_pair]

    def blit(
        self,
        renderer,
        cam_x: int,
        cam_y: int,
        vp_width: int,
        vp_height: int,
        dest_y: int = 0,
    ) -> None:
        win_max_y = math.floor(renderer.height) - 1
        win_max_x = math.floor(renderer.width) - 1

        for dy in range(vp_height):
            screen_y = dest_y + dy
            if screen_y >= win_max_y:
                break

            tile_y = cam_y + dy

            for dx in range(vp_width):
                screen_x = dx
                if screen_x >= win_max_x:
                    break

                tile_x = cam_x + dx
                tile = self.get_tile(tile_x, tile_y)

                if tile is not None:
                    char, color_pair = tile[0], tile[1]
                else:
                    char = self.default_char
                    color_pair = self.default_color_pair

                new_char = char if len(char) == 1 else self.default_char
                new_cp = color_pair if color_pair is not None else self.default_color_pair

                visibility = self.meta.get((tile_x, tile_y), {}).get("visibility", "visible")
                if visibility == "unseen":
                    renderer.set_cell(screen_x, screen_y, " ", None)
                    continue
                elif visibility == "explored":
                    if new_cp is not None:
                        fg, bg = new_cp
                        new_cp = (
                            (fg[0] // 2, fg[1] // 2, fg[2] // 2),
                            (bg[0] // 2, bg[1] // 2, bg[2] // 2),
                        )

                existing_char, existing_cp = renderer.get_cell(screen_x, screen_y)
                if new_char != existing_char or new_cp != existing_cp:
                    renderer.set_cell(screen_x, screen_y, new_char, new_cp)
