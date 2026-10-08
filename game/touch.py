"""Touch controls: taps and on-screen buttons become the same InputState a keyboard makes.

- Tapping a world tile walks there along a path (one step per move, like holding a
  direction). If the tile is something to act on (a gem, a diggable spot, a building,
  the dropped bag), the player uses it on arrival.
- Tapping an enemy next to the player attacks it; tapping the player's own tile uses it.
- Buttons press an action once; d-pad buttons can be held to keep moving.
"""

from game.enemies import find_path_bfs
from game.input import Action, InputState

_STEP_ACTIONS = {
    (-1, 0): Action.MOVE_LEFT,
    (1, 0): Action.MOVE_RIGHT,
    (0, -1): Action.MOVE_UP,
    (0, 1): Action.MOVE_DOWN,
}
_MOVES = frozenset(_STEP_ACTIONS.values())
# Buttons that stop a tap-walk in progress (moving by hand, fighting, recalling).
_INTERRUPTS = _MOVES | {Action.ATTACK, Action.USE, Action.RECALL}
# Longest walk a single tap plans (tiles).
MAX_TAP_PATH = 200


class TouchController:
    def __init__(self):
        self._pressed: set = set()
        self._held_buttons: set = set()
        self.path: list = []
        self._use_on_arrival = False

    # ── Buttons ───────────────────────────────────────────────────────────────

    def press(self, action: Action) -> None:
        """A button tap: the action fires once on the next poll."""
        if action in _INTERRUPTS:
            self.cancel_walk()
        self._pressed.add(action)

    def hold(self, action: Action, down: bool) -> None:
        """A d-pad button held down (or released)."""
        if down:
            self.cancel_walk()
            self._held_buttons.add(action)
        else:
            self._held_buttons.discard(action)

    def release_all(self) -> None:
        """Forget held buttons (e.g. the app lost focus mid-hold)."""
        self._held_buttons.clear()
        self.cancel_walk()

    def cancel_walk(self) -> None:
        self.path = []
        self._use_on_arrival = False

    # ── Taps on the world ─────────────────────────────────────────────────────

    def tap_world(self, state, x: int, y: int) -> None:
        here = (state.player_x, state.player_y)
        adjacent = max(abs(x - here[0]), abs(y - here[1])) <= 1
        if (x, y) == here or (adjacent and any((e.x, e.y) == (x, y) for e in state.enemies)):
            # Act where the player stands now: drop the walk and any turn it queued.
            self.cancel_walk()
            state.queued_move = None
            self._pressed.add(Action.USE if (x, y) == here else Action.ATTACK)
            return
        if state.world_tiles is None:
            return
        meta = state.world_tiles.meta

        def unseen(tx, ty):
            # Plan only through ground the player has seen: no shortcuts through fog.
            return meta.get((tx, ty), {}).get("visibility", "unseen") == "unseen"

        path = find_path_bfs(state.world_tiles, *here, x, y, max_steps=MAX_TAP_PATH, blocked=unseen)
        self.path = path
        self._use_on_arrival = bool(path) and path[-1] == (x, y) and _worth_using(state, x, y)

    # ── Per-frame output ──────────────────────────────────────────────────────

    def poll(self, state) -> InputState:
        """InputState for this frame; call once per frame.

        A walk step is sent as a press, not a hold: several simulation steps can run in
        one frame, and a held direction would then move more than one tile per path step.
        """
        held = set(self._held_buttons)
        here = (state.player_x, state.player_y)
        if state.active_scene != "game":
            self.cancel_walk()
        while self.path and self.path[0] == here:
            self.path.pop(0)
        if self.path:
            step = self.path[0]
            action = _STEP_ACTIONS.get((step[0] - here[0], step[1] - here[1]))
            if action is None:  # knocked off the path (e.g. recalled): give up
                self.cancel_walk()
            else:
                self._pressed.add(action)
        elif self._use_on_arrival:
            self._use_on_arrival = False
            self._pressed.add(Action.USE)
        pressed = frozenset(self._pressed)
        self._pressed.clear()
        return InputState(pressed=pressed, held=frozenset(held))


def _worth_using(state, x: int, y: int) -> bool:
    """Whether arriving at (x, y) should trigger USE (gem, dig spot, building, bag)."""
    if (x, y) in state.world_gems:
        return True
    bag = state.dropped_bag
    if bag is not None and (bag["x"], bag["y"]) == (x, y):
        return True
    meta = state.world_tiles.meta.get((x, y), {})
    return bool(meta.get("interactable")) and not meta.get("depleted")
