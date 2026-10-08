import time


class Clock:
    """Frame pacer based on a monotonic high-resolution timer.

    Frames are scheduled on fixed deadlines (start + n/fps) rather than "now + 1/fps",
    so OS sleep overshoot in one frame is absorbed by the next instead of accumulating.
    """

    def __init__(self, timer=time.perf_counter, sleep=time.sleep):
        self._timer = timer
        self._sleep = sleep
        self.last_tick = timer()
        self._deadline = self.last_tick

    def tick(self, fps: float) -> float:
        """Sleep until the next frame deadline, then return the full frame duration
        (work + sleep) in seconds."""
        period = 1 / fps
        self._deadline += period
        now = self._timer()
        if now < self._deadline:
            self._sleep(self._deadline - now)
            now = self._timer()
        elif now - self._deadline > period:
            # Fell more than a frame behind (e.g. a long load): resync instead of
            # rushing through back-to-back frames to catch up.
            self._deadline = now
        dt = now - self.last_tick
        self.last_tick = now
        return dt
