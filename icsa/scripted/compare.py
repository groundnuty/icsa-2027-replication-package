"""Compare a scripted run's outputs with the frozen ground truth of #5.

The reference is only what #5 froze: `cell_masks.npz` (checked against its sha256 in `instances.json`) and each
record's `events` and `active_mask`. Equality is exact: there is no tolerance, and a difference is reported with
its count and first locations, never adjusted away. `refdet.ground_truth` is deliberately not used here: it would
re-derive the reference with the code under test.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from pathlib import Path

import netCDF4
import numpy as np

from .. import grid


# Identifies the cell, and nothing more. The dataset stores its coordinates as float32: measured on S2, at most 3.97e-6
# deg from the 0.02-deg grid (a float32 ULP at 66 deg is 7.6e-6). 1e-5 deg is 1/2000 of a cell. Masks and events are exact.
COORD_ATOL_DEG = 1e-5


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 20):
            h.update(b)
    return h.hexdigest()


class FrozenTruth:
    """Per-instance truth from #5's manifest; refuses a mask file whose sha256 differs from the manifest's."""

    def __init__(self, manifest: dict, cell_masks_path: Path | str | None = None):
        self.records = {r["instance"]["instance_id"]: r for r in manifest["instances"]}
        path = Path(cell_masks_path or manifest["cell_masks"]["file"])
        want = manifest["cell_masks"]["sha256"]
        got = sha256_file(path)
        if got != want:
            raise ValueError(f"{path}: sha256 {got} differs from the manifest's {want}")
        self.sha256 = got
        self._path = path

    def cell_mask(self, iid: str) -> np.ndarray:
        rec = self.records[iid]
        i = rec["instance"]
        shape = (rec["target_days"][2], i["lat1"] - i["lat0"], i["lon1"] - i["lon0"])
        with np.load(self._path) as z:
            return np.unpackbits(z[iid], count=int(np.prod(shape))).reshape(shape).astype(bool)

    def events(self, iid: str) -> list[list[str]]:
        return [list(e) for e in self.records[iid]["events"]]

    def active_mask(self, iid: str) -> str:
        return self.records[iid]["active_mask"]


def read_mask_file(path: Path | str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(mask bool (time, lat, lon), day indices, lat, lon) from a run's mhw_mask.nc."""
    with netCDF4.Dataset(path) as nc:
        v = nc["mhw"]
        if v.dimensions != ("time", "lat", "lon"):
            raise ValueError(f"mhw has dimensions {v.dimensions}")
        v.set_auto_maskandscale(False)
        mask = np.asarray(v[:]) != 0
        t = nc["time"]
        base = str(t.units).removeprefix("days since ").strip()
        offset = (dt.date.fromisoformat(base[:10]) - grid.DAY0).days
        days = np.asarray(t[:], np.int64) + offset
        return mask, days, np.asarray(nc["lat"][:], np.float64), np.asarray(nc["lon"][:], np.float64)


def compare_mask(mask: np.ndarray, truth: np.ndarray, *, max_locations: int = 20) -> dict:
    if mask.shape != truth.shape:
        return {"equal": False, "reason": f"shape {mask.shape} != {truth.shape}", "differing_cell_days": None}
    diff = mask != truth
    n = int(diff.sum())
    out = {"equal": n == 0, "differing_cell_days": n, "cell_days": int(mask.sum()), "truth_cell_days": int(truth.sum())}
    if n:
        out["only_in_run"] = int((mask & ~truth).sum())
        out["only_in_truth"] = int((truth & ~mask).sum())
        out["first_differences"] = [[int(x) for x in loc] for loc in np.argwhere(diff)[:max_locations]]
    return out


def compare_run(truth: FrozenTruth, iid: str, mask_path: Path | str, report: dict, script_result: dict,
                expected_sst_sha256: str | None = None) -> dict:
    """Everything a run must match. `equal` is the AND of the parts; each part is reported on its own."""
    rec = truth.records[iid]
    i = rec["instance"]
    a, b = (dt.date.fromisoformat(x) for x in i["target"])
    want_days = np.arange(grid.day_index(a), grid.day_index(b) + 1, dtype=np.int64)
    mask, days, lat, lon = read_mask_file(mask_path)
    tmask = truth.cell_mask(iid)
    m = compare_mask(mask, tmask)
    days_ok = bool(np.array_equal(days, want_days))
    want_lat = grid.LAT_MIN + np.arange(i["lat0"], i["lat1"]) * grid.RES_DEG
    want_lon = grid.LON_MIN + np.arange(i["lon0"], i["lon1"]) * grid.RES_DEG
    coords_ok = bool(lat.size == want_lat.size and lon.size == want_lon.size
                     and np.allclose(lat, want_lat, atol=COORD_ATOL_DEG, rtol=0)
                     and np.allclose(lon, want_lon, atol=COORD_ATOL_DEG, rtol=0))
    t_events = truth.events(iid)
    r_events = [[e["onset"], e["end"]] for e in report.get("events", [])]
    active_ok = script_result.get("active_mask") == truth.active_mask(iid)
    out = {"mask": m, "days_equal": days_ok, "coords_equal": coords_ok,
           "events_equal": r_events == t_events, "events": r_events, "truth_events": t_events,
           "active_mask_equal": active_ok}
    parts = [m["equal"], days_ok, coords_ok, out["events_equal"], active_ok]
    # not checked = unknown (None), and an unknown part never makes a run equal
    out["sst_equal"] = None if expected_sst_sha256 is None else script_result.get("sst_sha256") == expected_sst_sha256
    parts.append(out["sst_equal"] is True)
    out["equal"] = all(parts)
    return out
