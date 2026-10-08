"""Fixed-timestep simulation driver (see "Fix Your Timestep", Glenn Fiedler)."""

from game.constants import FPS
from game.input import InputState

STEP = 1 / FPS
# Longest frame time simulated at once; longer stalls are dropped rather than replayed.
MAX_FRAME_DT = 0.25


class FixedTimestep:
    """Accumulates real frame time and releases it as fixed-size simulation steps.

    Pressed actions are buffered until a step consumes them, so a frame that runs zero
    steps never loses input, and a frame that runs several steps delivers them once.
    """

    def __init__(self, step: float = STEP, max_frame_dt: float = MAX_FRAME_DT):
        self.step = step
        self.max_frame_dt = max_frame_dt
        self.reset()

    def reset(self) -> None:
        """Forget accumulated time and input, e.g. when the simulation was paused.

        The next frame's duration is discarded too, since it covers the pause itself.
        The accumulator restarts at half a step: since STEP equals the frame period,
        starting at 0 would leave every frame on the step threshold, where sleep jitter
        alternates 0-step and 2-step frames (visible judder).
        """
        self.accumulator = self.step / 2
        self._pending = frozenset()
        self._discard_next_frame = True

    def run(self, frame_dt: float, inp: InputState, update) -> int:
        """Run as many fixed steps as the accumulated time allows.

        ``update(inp, dt)`` returns False to stop stepping early (e.g. the scene changed).
        Returns the number of steps run.
        """
        if self._discard_next_frame:
            frame_dt = 0.0
            self._discard_next_frame = False
        self.accumulator += min(frame_dt, self.max_frame_dt)
        self._pending |= inp.pressed

        steps = 0
        while self.accumulator >= self.step:
            self.accumulator -= self.step
            step_inp = InputState(pressed=self._pending, held=inp.held)
            self._pending = frozenset()
            steps += 1
            if not update(step_inp, self.step):
                break
        return steps
