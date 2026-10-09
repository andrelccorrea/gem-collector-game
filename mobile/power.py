"""Battery saver: draw fewer frames when fewer are needed.

Menus and the shop only change on input, and a player who has not touched the screen
for a while does not need 30 frames a second. The rate moves toward its target in steps
(never in jumps) and never drops below a floor. Plain data, tested without Kivy.
"""

FULL_FPS = 30
IDLE_FPS = 20  # in the world after IDLE_AFTER seconds without input
MENU_FPS = 15  # menus, shop, map: they only change on input
IDLE_AFTER = 10.0
STEP_FPS = 5


def target_fps(scene: str, idle_for: float, saver: bool) -> int:
    if not saver:
        return FULL_FPS
    if scene != "game":
        return MENU_FPS
    return IDLE_FPS if idle_for >= IDLE_AFTER else FULL_FPS


def next_fps(current: int, target: int) -> int:
    """One step from ``current`` toward ``target``; input wakes it to full at once."""
    if target > current and target == FULL_FPS:
        return FULL_FPS  # the player is back: respond immediately
    if current > target:
        return max(target, current - STEP_FPS)
    return min(target, current + STEP_FPS)
