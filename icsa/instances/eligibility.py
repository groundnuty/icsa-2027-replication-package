"""Box eligibility (science decision on #5, option (a)); same classification as #4's tools/diag/lakes.py.

finite = baseline-finite cells (seascan). bal = the bathymetry mask BALarea (`refdet.sea_mask`).
Components of finite & ~bal (8-connectivity) are classified as in lakes.py:
  coastal/lagoon  touches a BALarea cell (8-neighbour); open sea  touches the grid edge; lake  neither.
Rule 1 (Baltic): >= 95% of the box's finite cells lie inside BALarea.
Rule 2 (no inland water, refined by science): the box contains no cell of a 'lake' component of
>= INLAND_MIN (10) cells; pockets of fewer cells stay.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy import ndimage

from .. import grid
from ..extent import CellBox
from .boxes import box_counts

EIGHT = np.ones((3, 3), bool)
INLAND_MIN = 10   # a lake component of at least this many cells is inland water


@dataclasses.dataclass(frozen=True)
class Classes:
    finite: np.ndarray
    bal: np.ndarray
    lake: np.ndarray            # bool cells in lake components
    small_lake: np.ndarray      # bool cells in lake components of < INLAND_MIN cells (allowed)
    inland: np.ndarray          # bool cells in lake components of >= INLAND_MIN cells (excluded)
    labels: np.ndarray
    comp_size: np.ndarray       # indexed by label (0 unused)
    comp_kind: np.ndarray       # str, indexed by label


def classify(finite: np.ndarray, bal: np.ndarray) -> Classes:
    extra = finite & ~bal
    lab, n = ndimage.label(extra, structure=EIGHT)
    idx = np.arange(1, n + 1)
    size = np.concatenate([[0], ndimage.sum(np.ones_like(lab), lab, idx).astype(int)])
    touch = ndimage.binary_dilation(bal, structure=EIGHT)
    adj = np.concatenate([[False], ndimage.maximum(touch, lab, idx).astype(bool)])
    edge = np.zeros_like(extra)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    at_edge = np.concatenate([[False], ndimage.maximum(edge, lab, idx).astype(bool)])
    kind = np.where(adj, "coastal/lagoon", np.where(at_edge, "open sea", "lake"))
    kind[0] = ""
    lake_comp = kind == "lake"
    lake = lake_comp[lab]
    small = (lake_comp & (size < INLAND_MIN))[lab]
    inland = (lake_comp & (size >= INLAND_MIN))[lab]
    return Classes(finite, bal, lake, small, inland, lab, size, kind)


def eligible_mask(c: Classes, h: int, w: int, min_baltic: float = 0.95):
    """Per box start (j, i): (rule1, rule2, rule2_only_tiny) boolean arrays."""
    fin = box_counts(c.finite, h, w)
    inbal = box_counts(c.finite & c.bal, h, w)
    r1 = inbal >= min_baltic * fin
    inland = box_counts(c.inland, h, w)
    any_lake = box_counts(c.lake, h, w)
    r2 = inland == 0
    small_only = (any_lake > 0) & r2        # holds lake cells, all of them in allowed small pockets
    return r1, r2, small_only
