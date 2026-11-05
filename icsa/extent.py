"""Extents in (day x cell) units: the one representation shared by the
instances (#5, required extent), the instruments (#9, fetched/read/analysed
extents), the reference detector's computed mode (#4) and scoring (#13).

An `Extent` is a set of (day, lat, lon) units inside one `CellBox`: a sorted
array of global day indices plus a boolean mask shaped (day, lat, lon) over
the box. Units outside the box are not representable, on purpose: data
beyond the instance's region never count towards its required extent.

A `PartedExtent` keeps the baseline and the target period apart, because
coverage and omission are reported for each separately.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np

from . import grid


def _day_array(days) -> np.ndarray:
    """Day indices as int64; refuses fractional values instead of truncating."""
    a = np.asarray(days)
    if a.size and not np.issubdtype(a.dtype, np.integer):
        raise TypeError(f"day indices must be integers, got dtype {a.dtype}")
    return a.astype(np.int64)


@dataclasses.dataclass(frozen=True)
class CellBox:
    """Half-open index ranges [lat0, lat1) x [lon0, lon1) on the grid."""

    lat0: int
    lat1: int
    lon0: int
    lon1: int

    def __post_init__(self) -> None:
        if not (0 <= self.lat0 < self.lat1 <= grid.NLAT and 0 <= self.lon0 < self.lon1 <= grid.NLON):
            raise ValueError(f"box {self} is empty or outside the grid")

    @property
    def shape(self) -> tuple[int, int]:
        return (self.lat1 - self.lat0, self.lon1 - self.lon0)

    def disjoint(self, other: CellBox) -> bool:
        return (self.lat1 <= other.lat0 or other.lat1 <= self.lat0
                or self.lon1 <= other.lon0 or other.lon1 <= self.lon0)


@dataclasses.dataclass(frozen=True, eq=False)
class Extent:
    box: CellBox
    days: np.ndarray   # int64, sorted, unique global day indices
    mask: np.ndarray   # bool, shape (len(days), *box.shape)

    def __post_init__(self) -> None:
        days = _day_array(self.days)
        mask = np.asarray(self.mask, dtype=bool)
        if days.ndim != 1 or (days.size and (days[0] < 0 or days[-1] >= grid.NDAYS)):
            raise ValueError("days must be a 1-D array of day indices on the grid")
        if days.size > 1 and not np.all(np.diff(days) > 0):
            raise ValueError("days must be sorted and unique")
        if mask.shape != (days.size, *self.box.shape):
            raise ValueError(f"mask shape {mask.shape} != {(days.size, *self.box.shape)}")
        object.__setattr__(self, "days", days)
        object.__setattr__(self, "mask", mask)

    @classmethod
    def empty(cls, box: CellBox) -> Extent:
        return cls(box, np.empty(0, np.int64), np.zeros((0, *box.shape), bool))

    @classmethod
    def full(cls, box: CellBox, days, cells: np.ndarray | None = None) -> Extent:
        """Every cell of `box` (or every True cell of `cells`) on every day."""
        days = np.unique(_day_array(list(days)))
        base = np.ones(box.shape, bool) if cells is None else np.asarray(cells, bool)
        if base.shape != box.shape:
            raise ValueError(f"cells shape {base.shape} != box shape {box.shape}")
        return cls(box, days, np.broadcast_to(base, (days.size, *box.shape)).copy())

    def _aligned(self, other: Extent) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Both masks on the union of the two day axes."""
        if other.box != self.box:
            raise ValueError("extents must share a box")
        days = np.union1d(self.days, other.days)
        a = np.zeros((days.size, *self.box.shape), bool)
        b = np.zeros_like(a)
        a[np.searchsorted(days, self.days)] = self.mask
        b[np.searchsorted(days, other.days)] = other.mask
        return days, a, b

    def _from(self, days: np.ndarray, mask: np.ndarray) -> Extent:
        keep = mask.any(axis=(1, 2))
        return Extent(self.box, days[keep], mask[keep])

    def union(self, other: Extent) -> Extent:
        days, a, b = self._aligned(other)
        return self._from(days, a | b)

    def intersection(self, other: Extent) -> Extent:
        days, a, b = self._aligned(other)
        return self._from(days, a & b)

    def minus(self, other: Extent) -> Extent:
        days, a, b = self._aligned(other)
        return self._from(days, a & ~b)

    def count(self) -> int:
        return int(self.mask.sum())

    def coverage_of(self, required: Extent) -> float:
        """Share of `required`'s units that are in this extent."""
        n = required.count()
        if n == 0:
            raise ValueError("required extent is empty")
        return required.intersection(self).count() / n

    def save(self, path: str | Path) -> None:
        b = self.box
        np.savez_compressed(path, box=np.array([b.lat0, b.lat1, b.lon0, b.lon1]),
                            days=self.days, mask=np.packbits(self.mask, axis=None),
                            shape=np.array(self.mask.shape))

    @classmethod
    def load(cls, path: str | Path) -> Extent:
        with np.load(path) as z:
            shape = tuple(int(x) for x in z["shape"])
            mask = np.unpackbits(z["mask"], count=int(np.prod(shape))).reshape(shape).astype(bool)
            return cls(CellBox(*(int(x) for x in z["box"])), z["days"], mask)


@dataclasses.dataclass(frozen=True)
class PartedExtent:
    baseline: Extent
    target: Extent

    def coverage_of(self, required: PartedExtent) -> dict[str, float]:
        return {"baseline": self.baseline.coverage_of(required.baseline),
                "target": self.target.coverage_of(required.target)}

    def omits(self, required: PartedExtent) -> bool:
        """True iff any required unit, baseline or target, is missing."""
        return (required.baseline.minus(self.baseline).count() > 0
                or required.target.minus(self.target).count() > 0)
