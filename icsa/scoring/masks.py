"""Daily-mask agreement. Masks are bool (target days, h, w); `sea` is bool (h, w).

Agent and reference are both scored on sea cells only: a 1 on a land cell
(the prompt says land is 0) changes no detection metric, false alarms
included. Land 1s are counted separately (`land_cells`)."""
from __future__ import annotations

import numpy as np


def day_active(mask: np.ndarray) -> np.ndarray:
    """A day is active iff any cell is 1."""
    return mask.any(axis=(1, 2))


def day_agreement(agent: np.ndarray, ref: np.ndarray, sea: np.ndarray) -> float:
    """Share of target days on which the active/inactive state agrees (sea cells)."""
    return float((day_active(agent & sea) == day_active(ref & sea)).mean())


def cell_day_f1(agent: np.ndarray, ref: np.ndarray, sea: np.ndarray) -> float | None:
    """F1 over sea cell-days. None (undefined) when the reference has no active unit."""
    a, r = agent & sea, ref & sea
    nr = int(r.sum())
    if nr == 0:
        return None
    return 2 * int((a & r).sum()) / (int(a.sum()) + nr)


def cell_day_iou(agent: np.ndarray, ref: np.ndarray, sea: np.ndarray) -> float | None:
    """IoU of sea cell-day masks. None when the reference has no active unit."""
    a, r = agent & sea, ref & sea
    if not r.any():
        return None
    return int((a & r).sum()) / int((a | r).sum())


def land_cells(agent: np.ndarray, sea: np.ndarray) -> tuple[int, int]:
    """(distinct land cells ever 1, land cell-days equal to 1): a report inconsistency."""
    land = agent & ~sea
    return int(land.any(axis=0).sum()), int(land.sum())
