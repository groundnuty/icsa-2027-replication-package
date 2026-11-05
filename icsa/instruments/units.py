"""Build `PartedExtent`s from arrays of global (day, lat, lon) unit indices."""
from __future__ import annotations

import numpy as np

from .. import grid
from ..extent import CellBox, Extent, PartedExtent


def _arrays(day, lat, lon) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    out = []
    for name, a in (("day", day), ("lat", lat), ("lon", lon)):
        a = np.asarray(a)
        if a.size and not np.issubdtype(a.dtype, np.integer):
            raise TypeError(f"{name} indices must be integers, got dtype {a.dtype}")
        if a.ndim != 1:
            a = a.reshape(-1)
        out.append(a.astype(np.int64, copy=False))
    if not (out[0].size == out[1].size == out[2].size):
        raise ValueError("day, lat and lon must have equal length")
    return out[0], out[1], out[2]


def _period(days) -> np.ndarray:
    return np.unique(np.asarray(list(days), dtype=np.int64))


def _in_box(lat: np.ndarray, lon: np.ndarray, box: CellBox) -> np.ndarray:
    return (lat >= box.lat0) & (lat < box.lat1) & (lon >= box.lon0) & (lon < box.lon1)


def _extent(day, lat, lon, box: CellBox, period: np.ndarray) -> Extent:
    sel = np.isin(day, period)
    if not sel.any():
        return Extent.empty(box)
    d, la, lo = day[sel], lat[sel], lon[sel]
    days, pos = np.unique(d, return_inverse=True)
    mask = np.zeros((days.size, *box.shape), bool)
    mask[pos.reshape(-1), la - box.lat0, lo - box.lon0] = True
    return Extent(box, days, mask)


def parted(day, lat, lon, box: CellBox, baseline_days, target_days) -> PartedExtent:
    """Baseline and target extents of the units inside `box`.

    A unit is kept if it is inside `box` (half-open) and its day is in the
    period. Duplicates collapse; a day in neither period is dropped.
    """
    day, lat, lon = _arrays(day, lat, lon)
    keep = _in_box(lat, lon, box)
    day, lat, lon = day[keep], lat[keep], lon[keep]
    return PartedExtent(_extent(day, lat, lon, box, _period(baseline_days)),
                        _extent(day, lat, lon, box, _period(target_days)))


def beyond(day, lat, lon, box: CellBox, baseline_days, target_days) -> int:
    """Number of distinct units outside `box` or outside both periods."""
    day, lat, lon = _arrays(day, lat, lon)
    if day.size == 0:
        return 0
    inside = _in_box(lat, lon, box)
    in_period = np.isin(day, np.union1d(_period(baseline_days), _period(target_days)))
    out = ~(inside & in_period)
    if not out.any():
        return 0
    # Row-wise unique: units here may lie anywhere (even off-grid).
    d, la, lo = day[out], lat[out], lon[out]
    key = np.stack([d, la, lo], axis=1)
    return int(np.unique(key, axis=0).shape[0])


class UnitTally:
    """`parted` and `beyond` of units added piece by piece, without holding the units.

    What a byte log covers does not depend on the instance's box: one T run on S1 covers 1e9 units and a whole S2 file
    1e10, and holding those as (day, lat, lon) arrays took over 60 GiB for one label (#9, 2 Nov). Here a day holds one
    packed bitmap of the grid, at most 82 KB, and days with the same whole chunks share it, as on every real file
    (a chunk is a whole day's grid). Units must be on the grid; `layout._axis_index` guarantees it for a built index.
    """

    def __init__(self, box: CellBox, baseline_days, target_days):
        self.box = box
        self._baseline, self._target = _period(baseline_days), _period(target_days)
        self.days: dict[int, bytes] = {}                         # day -> its cells, packed
        self._blocks: dict[tuple[bytes, bytes], bytes] = {}      # (rows, columns) -> those cells, one object
        self._counts: dict[bytes, tuple[int, int]] = {}          # cells -> units, units in the box

    @staticmethod
    def _on_grid(lat: np.ndarray, lon: np.ndarray) -> None:
        if lat.min() < 0 or lat.max() >= grid.NLAT or lon.min() < 0 or lon.max() >= grid.NLON:
            raise ValueError("a unit lies outside the grid")

    def _put(self, day: int, cells: bytes) -> None:
        old = self.days.get(day)
        if old is not None and old is not cells:
            cells = np.bitwise_or(np.frombuffer(old, np.uint8), np.frombuffer(cells, np.uint8)).tobytes()
        self.days[day] = cells

    def add_block(self, days, lats, lons) -> None:
        """Every unit of days x lats x lons."""
        lats, lons = np.asarray(lats, np.int64).reshape(-1), np.asarray(lons, np.int64).reshape(-1)    # flat, as `parted` takes units
        if not (np.size(days) and lats.size and lons.size):
            return
        key = (lats.tobytes(), lons.tobytes())
        cells = self._blocks.get(key)
        if cells is None:
            self._on_grid(lats, lons)
            m = np.zeros((grid.NLAT, grid.NLON), bool)
            m[np.ix_(lats, lons)] = True
            cells = self._blocks[key] = np.packbits(m).tobytes()
        for d in np.asarray(days, np.int64).reshape(-1).tolist():
            self._put(d, cells)

    def add_units(self, day, lat, lon) -> None:
        """The units listed; duplicates collapse."""
        day, lat, lon = _arrays(day, lat, lon)
        if not day.size:
            return
        self._on_grid(lat, lon)
        for d in np.unique(day).tolist():
            sel = day == d
            m = np.zeros((grid.NLAT, grid.NLON), bool)
            m[lat[sel], lon[sel]] = True
            self._put(d, np.packbits(m).tobytes())

    def _in_box(self, cells: bytes) -> np.ndarray:
        m = np.unpackbits(np.frombuffer(cells, np.uint8), count=grid.NLAT * grid.NLON).reshape(grid.NLAT, grid.NLON)
        b = self.box
        return m[b.lat0:b.lat1, b.lon0:b.lon1].astype(bool)

    def _counted(self, cells: bytes) -> tuple[int, int]:
        c = self._counts.get(cells)
        if c is None:
            total = int(np.bitwise_count(np.frombuffer(cells, np.uint8)).sum())
            c = self._counts[cells] = (total, int(self._in_box(cells).sum()))
        return c

    def _extent(self, period: np.ndarray) -> Extent:
        wanted = set(period.tolist())
        days = sorted(d for d, cells in self.days.items() if d in wanted and self._counted(cells)[1])
        if not days:
            return Extent.empty(self.box)
        mask = np.zeros((len(days), *self.box.shape), bool)
        for k, d in enumerate(days):
            mask[k] = self._in_box(self.days[d])
        return Extent(self.box, np.array(days, np.int64), mask)

    def parted(self) -> PartedExtent:
        """As `parted` of the same units."""
        return PartedExtent(self._extent(self._baseline), self._extent(self._target))

    def beyond(self) -> int:
        """As `beyond` of the same units."""
        required = set(self._baseline.tolist()) | set(self._target.tolist())
        out = 0
        for d, cells in self.days.items():
            total, in_box = self._counted(cells)
            out += total - in_box if d in required else total
        return out
