"""Host-memory watchdog: pause dispatch when the host's available memory runs low, resume by itself, kill nothing.

The sandboxes' memory limits add up to more than the host has (8 x 16 GiB against 55 GB, accepted by the science agent as
overcommit); this is the guard. It only holds back NEW runs: a run in flight is never touched, so a pause changes when runs
start and never how any run ends. Pause below `pause_below_bytes`, resume at or above `resume_at_bytes` (hysteresis, so it
does not flap). An unreadable meminfo is `unknown`: it never pauses and never resumes, and is said so.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

GiB = 1024 ** 3


def read_mem_available(path: str = "/proc/meminfo") -> int | None:
    """MemAvailable in bytes, or None when it cannot be read."""
    try:
        for line in Path(path).read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except Exception:  # noqa: BLE001
        pass
    return None


class HostMemoryWatchdog:
    def __init__(self, pause_below_gib: float | None, resume_at_gib: float | None,
                 reader: Callable[[], int | None] = read_mem_available):
        self.enabled = bool(pause_below_gib)
        if self.enabled:
            resume = pause_below_gib if resume_at_gib is None else resume_at_gib
            if resume < pause_below_gib:
                raise ValueError("host_mem_resume_at_gib must not be below host_mem_pause_below_gib")
            self.pause_below, self.resume_at = pause_below_gib * GiB, resume * GiB
        self.reader = reader
        self.paused = False
        self.available: int | None = None

    def check(self) -> tuple[bool, str | None]:
        """Read memory now. Returns (paused, transition): transition is "pause", "resume" or None."""
        if not self.enabled:
            return False, None
        self.available = self.reader()
        if self.available is None:
            return self.paused, None            # unknown: keep the state, decide nothing
        if not self.paused and self.available < self.pause_below:
            self.paused = True
            return True, "pause"
        if self.paused and self.available >= self.resume_at:
            self.paused = False
            return False, "resume"
        return self.paused, None
