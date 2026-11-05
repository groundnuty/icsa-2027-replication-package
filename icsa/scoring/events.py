"""Event matching. An event is a set of active (day, cell) units.

Units are flat indices into the (target day, lat, lon) array. A candidate
pair is any two events with at least one unit in common; the matching is
one-to-one, maximising the number of pairs first and the total overlap second
(protocol: maximum cardinality, overlap as the tie-breaker).
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy.optimize import linear_sum_assignment


def span(days: np.ndarray, onset: int, end: int) -> tuple[int, int]:
    """Half-open positions [i0, i1) on `days` of the days in [onset, end]."""
    return int(np.searchsorted(days, onset, "left")), int(np.searchsorted(days, end, "right"))


def event_units(cell_mask: np.ndarray, i0: int, i1: int) -> np.ndarray:
    """Flat unit indices of the active cells of `cell_mask` (n, h, w) on days [i0, i1)."""
    hw = cell_mask.shape[1] * cell_mask.shape[2]
    return np.flatnonzero(cell_mask[i0:i1]) + i0 * hw


@dataclasses.dataclass(frozen=True)
class Match:
    n_agent: int
    n_ref: int
    tp: int
    precision: float | None   # None when there is no agent event
    recall: float | None      # None when there is no reference event
    f1: float | None          # None when there is no reference event (undefined)
    merges: int               # agent events overlapping >= 2 reference events
    splits: int               # reference events overlapped by >= 2 agent events
    pairs: tuple[tuple[int, int], ...]  # matched (agent index, reference index)


def overlap_matrix(agent: list[np.ndarray], ref: list[np.ndarray]) -> np.ndarray:
    o = np.zeros((len(agent), len(ref)), dtype=np.int64)
    for i, a in enumerate(agent):
        for j, r in enumerate(ref):
            o[i, j] = np.intersect1d(a, r, assume_unique=True).size
    return o


def match_events(agent: list[np.ndarray], ref: list[np.ndarray]) -> Match:
    """Agent events: unit arrays must be unique within an event."""
    o = overlap_matrix(agent, ref)
    pairs: list[tuple[int, int]] = []
    if o.size:
        # lexicographic (pairs, overlap): BIG exceeds any possible total overlap
        big = int(o.sum()) + 1
        w = big * (o > 0).astype(np.int64) + o
        rows, cols = linear_sum_assignment(w, maximize=True)
        pairs = [(int(r), int(c)) for r, c in zip(rows, cols) if o[r, c] > 0]
    tp, na, nr = len(pairs), len(agent), len(ref)
    return Match(
        n_agent=na, n_ref=nr, tp=tp,
        precision=tp / na if na else None,
        recall=tp / nr if nr else None,
        f1=2 * tp / (na + nr) if nr else None,
        merges=int(((o > 0).sum(axis=1) >= 2).sum()) if o.size else 0,
        splits=int(((o > 0).sum(axis=0) >= 2).sum()) if o.size else 0,
        pairs=tuple(pairs))


def active_runs(active: np.ndarray) -> list[tuple[int, int]]:
    """Maximal runs of consecutive True days, as half-open position pairs."""
    a = np.concatenate(([False], np.asarray(active, bool), [False]))
    edges = np.flatnonzero(a[1:] != a[:-1])
    return [(int(s), int(e)) for s, e in zip(edges[::2], edges[1::2])]
