"""One process-wide lock for every netCDF4 / HDF5 / h5py read or write done from worker threads.

netCDF4 and HDF5 are not safe for concurrent use from several threads of one process (a six-thread read crashed the
interpreter with SIGSEGV). The harness and the campaign run `execute_run` and scoring on worker threads, so every
read that can be reached from a thread takes this lock. Re-entrant, so a locked function may call another.

Time spent WAITING for the lock is measured per thread (`thread_wait_s`), so a run can keep it out of its measured
wall time and record it.
"""
import threading
import time

_local = threading.local()


class _TimedRLock:
    def __init__(self):
        self._lock = threading.RLock()

    def acquire(self, blocking=True, timeout=-1):
        t = time.monotonic()
        ok = self._lock.acquire(blocking, timeout)
        _local.waited = getattr(_local, "waited", 0.0) + (time.monotonic() - t)
        return ok

    def release(self):
        self._lock.release()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


NETCDF_LOCK = _TimedRLock()


def thread_wait_s() -> float:
    """Total seconds this thread has spent waiting for NETCDF_LOCK so far."""
    return getattr(_local, "waited", 0.0)
