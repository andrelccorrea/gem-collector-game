import curses
import math
import os
import sys

from . import clock, keyboard, util


class Window:
    def __init__(self, width=80, height=22, char=" ", fps=60):
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

    def start(self, func):
        try:
            self.screen = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)
            self.screen.nodelay(True)
            self.screen.keypad(True)
            self.running = True
            self.clock = clock.Clock()
            self.keyboard = keyboard.Keyboard(self)
            self.color_pairs = util.ColorPairs(self)
            self.color_pair = ((255, 255, 255), (0, 0, 0))
            self.color_pairs.add(self.color_pair)
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

    def exit(self):
        self.running = False
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

    def update(self, fps):
        self.screen.getch()
        for y in range(math.floor(self.height)):
            for x in range(math.floor(self.width)):
                if y != math.floor(self.height) - 1 and x != math.floor(self.width) - 1:
                    try:
                        if self.screen_array[y][x][0]:  # if that particular point is changed...
                            if curses.can_change_color():
                                color_pair = self.screen_array[y][x][2]
                                if color_pair:
                                    self.screen.addstr(
                                        y,
                                        x,
                                        self.screen_array[y][x][1],
                                        self.color_pairs.get_color_pair(color_pair),
                                    )
                                else:
                                    self.screen_array[y][x][2] = self.color_pair
                                    self.screen.addstr(
                                        y,
                                        x,
                                        self.screen_array[y][x][1],
                                        self.color_pairs.get_color_pair(self.color_pair),
                                    )
                            else:
                                self.screen.addstr(
                                    y, x, self.screen_array[y][x][1], curses.color_pair(0)
                                )
                        self.screen_array[y][x][0] = False
                    except curses.error:
                        # Raised when the terminal is smaller than screen_array.
                        self.screen.resize(math.floor(self.height), math.floor(self.width))
        self.screen.refresh()
        self.clock.update()
        self.clock.delay(1 / fps)
