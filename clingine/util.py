import curses
import math
import os


# rgb values range from 0 to 255
class Colors:
    def __init__(self):
        self.colors = {}

    def add(self, *rgbs):
        for rgb in rgbs:
            color_number = self.generate_color_number()
            self.colors[rgb] = color_number
            # interpolate RGB to 0–1000 range for curses
            rgb = self.interpolate(rgb)
            curses.init_color(color_number, rgb[0], rgb[1], rgb[2])

    def remove(self, *rgbs):
        for rgb in rgbs:
            del self.colors[rgb]

    def interpolate(self, rgb):
        interpolated = []
        for i in rgb:
            x = i * 1000 // 255
            interpolated.append(x)
        return tuple(interpolated)

    def generate_color_number(self):
        nums = sorted([self.colors[key] for key in self.colors])
        if len(nums) == 0:
            return 1
        i = 0
        while i < len(nums):
            if i + 1 != nums[i]:
                return i + 1
            i += 1
        return (i + 1) % (curses.COLORS + 1)


class ColorPairs:
    def __init__(self, window):
        self.window = window
        self.colors = Colors()
        self.color_pairs = {}

    def add(self, *rgb_pairs):
        for rgb_pair in rgb_pairs:
            color_pair_number = self.generate_color_pair_number()
            self.color_pairs[rgb_pair] = color_pair_number
            fg_color_number = self.colors.colors.get(rgb_pair[0], False)
            bg_color_number = self.colors.colors.get(rgb_pair[1], False)
            if not fg_color_number:
                self.colors.add(rgb_pair[0])
                fg_color_number = self.colors.colors[rgb_pair[0]]
            if not bg_color_number:
                self.colors.add(rgb_pair[1])
                bg_color_number = self.colors.colors[rgb_pair[1]]
            curses.init_pair(color_pair_number, fg_color_number, bg_color_number)

    def remove(self, *rgb_pairs):
        for rgb_pair in rgb_pairs:
            del self.color_pairs[rgb_pair]

    def generate_color_pair_number(self):
        nums = sorted([self.color_pairs[key] for key in self.color_pairs])
        if len(nums) == 0:
            return 1
        i = 0
        while i < len(nums):
            if i + 1 != nums[i]:
                return i + 1
            i += 1
        return (i + 1) % (curses.COLOR_PAIRS)

    def get_color_pair(self, rgb_pair):
        rgb_pair_buffer = []
        for i in range(len(rgb_pair)):
            if not rgb_pair[i]:
                rgb_pair_buffer.append(self.window.color_pair[i])
            else:
                rgb_pair_buffer.append(rgb_pair[i])
        rgb_pair = tuple(rgb_pair_buffer)
        color_pair_number = self.color_pairs.get(rgb_pair, False)
        if not color_pair_number:
            self.add(rgb_pair)
            color_pair_number = self.color_pairs[rgb_pair]
        return curses.color_pair(color_pair_number)


class Image:
    def __init__(self, value, source, width, height):
        self.value = value
        self.source = source
        self.width = width
        self.height = height


def load_image(source):
    val = []
    with open(source) as file:
        lines = file.readlines()
        height = len(lines)
        width = 0
        for line in lines:
            if len(line) - 1 > width:
                width = len(line) - 1
            val.append(line.rstrip("\n"))
    val = tuple(val)
    img = Image(val, source, width, height)
    return img


def load_images(source):
    imgs = []
    files = sorted(os.listdir(source), key=lambda name: int(name.split("_")[1].split(".")[0]))
    for file in files:
        imgs.append(load_image(f"{source}/{file}"))
    return imgs


def draw_line(renderer, x1: int, x2: int, y: int, char: str, color_pair) -> None:
    y = math.floor(y)
    if x1 > x2:
        x1, x2 = x2, x1
    x1 = x1 if x1 > 0 else 0
    x2 = x2 if x2 < renderer.width - 2 else renderer.width - 2
    for x in range(math.floor(x1), math.floor(x2) + 1):
        if 0 <= y <= renderer.height - 2:
            existing_char, existing_cp = renderer.get_cell(x, y)
            if existing_char != char or existing_cp != color_pair:
                renderer.set_cell(x, y, char, color_pair)


def draw_endpoints(renderer, x1: int, x2: int, y: int, char: str, color_pair) -> None:
    y = math.floor(y)
    x1 = math.floor(x1)
    x2 = math.floor(x2)
    if 0 <= x1 <= renderer.width - 2 and 0 <= y <= renderer.height - 2:
        existing_char, existing_cp = renderer.get_cell(x1, y)
        if existing_char != char or existing_cp != color_pair:
            renderer.set_cell(x1, y, char, color_pair)
    if 0 <= x2 <= renderer.width - 2 and 0 <= y <= renderer.height - 2:
        existing_char, existing_cp = renderer.get_cell(x2, y)
        if existing_char != char or existing_cp != color_pair:
            renderer.set_cell(x2, y, char, color_pair)
