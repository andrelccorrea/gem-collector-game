import curses
import math
import os
import sys

from . import clock, colors, keyboard


class Window:
    def __init__(self, width=80, height=22, char=" ", fps=60, glyph_fallback=None):
        if sys.platform == "win32" or sys.platform == "cygwin":
            os.system(f"mode {width}, {height}")
        else:
            # Ask the terminal to resize itself; the trailing print flushes the escape sequence
            # so the new dimensions apply before curses initializes.
            sys.stdout.write(f"\x1b[8;{height};{width}t")
            print()
        self.width = width
        self.height = height
        self.char = char
        self.fps = fps
        # Replacement characters for terminals whose encoding is not UTF-8.
        self.glyph_fallback = glyph_fallback or {}
        self._fallback = {}

    def start(self, func):
        try:
            self.screen = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)
            self.screen.nodelay(True)
            self.screen.keypad(True)
            # Deliver a lone Esc after 25 ms instead of the 1 s escape-sequence default.
            curses.set_escdelay(25)
            if self.screen.encoding.lower().replace("-", "") != "utf8":
                self._fallback = self.glyph_fallback
            self.running = True
            self.clock = clock.Clock()
            self.keyboard = keyboard.Keyboard(self.screen)
            self.color_pairs = colors.ColorPairs(
                curses.COLORS, curses.COLOR_PAIRS, curses.init_pair, curses.color_pair
            )
            self.color_pair = ((255, 255, 255), (0, 0, 0))
            self.fill(self.color_pair)
            self.reset()
            func()  # the main game loop
            self.exit()

        except Exception as e:
            self.exit()
            raise e

    def fill(self, color_pair):
        self.color_pair = color_pair
        color_pair = self.color_pairs.get_color_pair(color_pair)
        self.screen.bkgd(self.char, color_pair)

    def reset(self):

        # 2D array of [is_changed, char, color_pair] cells; is_changed marks cells to redraw.
        self.screen_array = []
        for _ in range(math.floor(self.height)):
            self.screen_array.append(
                [[True, self.char, self.color_pair] for _ in range(math.floor(self.width))]
            )
        self._forget_drawn()

    def _forget_drawn(self):
        """Assume the terminal shows nothing we drew (first frame, or after a resize
        wiped it), so every cell is drawn again on the next update."""
        # What the terminal currently shows per cell; None means unknown.
        self._drawn = [[None] * math.floor(self.width) for _ in range(math.floor(self.height))]
        for row in self.screen_array:
            for cell in row:
                cell[0] = True
        self._terminal_size = None

    def exit(self):
        self.running = False
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

    def update(self):
        """Draw the cells whose content changed since they were last drawn."""
        size = self.screen.getmaxyx()
        if size != self._terminal_size:
            if self._terminal_size is not None:
                self._forget_drawn()
            self._terminal_size = size
        rows, cols = math.floor(self.height) - 1, math.floor(self.width) - 1
        for y in range(rows):
            row, drawn = self.screen_array[y], self._drawn[y]
            for x in range(cols):
                cell = row[x]
                if not cell[0]:
                    continue
                cell[0] = False
                # A cell may be rewritten several times per frame (e.g. cleared and then
                # redrawn with the same text); only an actual change reaches the terminal.
                content = (cell[1], cell[2] or self.color_pair)
                if drawn[x] == content:
                    continue
                try:
                    char = self._fallback.get(content[0], content[0])
                    self.screen.addstr(y, x, char, self.color_pairs.get_color_pair(content[1]))
                    drawn[x] = content
                except curses.error:
                    # Raised when the terminal is smaller than screen_array; retry the cell
                    # next frame.
                    cell[0] = True
                    self.screen.resize(math.floor(self.height), math.floor(self.width))
        self.screen.refresh()
