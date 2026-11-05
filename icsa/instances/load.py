"""Loaders for the committed instance manifests (#5): the exact required extent.

data/instances/{boxes.json, sea_masks.npz, instances.json}. The sea mask is time-invariant per
region (checked at generation: finite on every day of 1991-12-27..2023-12-30; sea = finite on every target day), so one mask per
region serves both of its instances.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np

from ..extent import CellBox, Extent, PartedExtent
from ..records import Instance, Period
from . import required as R

DATA = Path(__file__).resolve().parents[2] / "data" / "instances"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_sea_masks(path: Path | str | None = None, expect_sha256: str | None = None) -> dict[str, np.ndarray]:
    path = Path(path or DATA / "sea_masks.npz")
    if expect_sha256 and sha256(path) != expect_sha256:
        raise ValueError(f"{path} does not match the recorded sha256")
    with np.load(path) as z:
        shape = tuple(int(x) for x in z["shape"])
        return {k: np.unpackbits(z[k], count=shape[0] * shape[1]).reshape(shape).astype(bool)
                for k in z.files if k != "shape"}


def load_instances(path: Path | str | None = None) -> dict:
    return json.loads(Path(path or DATA / "instances.json").read_text())


def required_extent(rec: dict, sea: np.ndarray) -> PartedExtent:
    """The required extent of one instance record (`instances.json` entry) from its box, target
    period and the region's sea mask: method-required baseline days (1,452 for Jun-Aug) and target days x the sea mask."""
    i = rec["instance"]
    box = CellBox(i["lat0"], i["lat1"], i["lon0"], i["lon1"])
    s, e = (dt.date.fromisoformat(x) for x in i["target"])
    ext = R.required_extent(box, sea, s, e)
    if ext.baseline.days.size != rec["baseline_days"]:
        raise ValueError(f"{i['instance_id']}: baseline has {ext.baseline.days.size} days, record says {rec['baseline_days']}")
    return ext


def instance(rec: dict) -> Instance:
    """The shared `icsa.records.Instance` of a manifest record; `pilot` and `calibration` come from
    the manifest flags (`calibration` is the record-level flag, the one the campaign selects by)."""
    i = rec["instance"]
    fields = {k: v for k, v in i.items() if k not in ("target", "pilot", "calibration")}
    return Instance(**fields, target=Period(*(dt.date.fromisoformat(x) for x in i["target"])),
                    pilot=bool(i["pilot"]), calibration=bool(rec["calibration"]))


def load_all_instances(manifest: dict | None = None) -> list[Instance]:
    return [instance(r) for r in (manifest or load_instances())["instances"]]


def load_required_extents(manifest: dict | None = None, data: Path | str | None = None) -> dict[str, PartedExtent]:
    """instance id -> PartedExtent, verifying the mask file against the manifest's sha256 and the
    per-record sea-cell counts."""
    data = Path(data or DATA)
    m = manifest or load_instances(data / "instances.json")
    masks = load_sea_masks(data / m["sea_masks"]["file"], m["sea_masks"]["sha256"])
    out = {}
    for rec in m["instances"]:
        sea = masks[rec["instance"]["region_id"]]
        if int(sea.sum()) != rec["sea_cells"]:
            raise ValueError(f"{rec['instance']['instance_id']}: mask has {int(sea.sum())} cells, "
                             f"record says {rec['sea_cells']}")
        out[rec["instance"]["instance_id"]] = required_extent(rec, sea)
    return out


def required_day_indices(rec: dict) -> np.ndarray:
    """THE derivation of an instance's required days: the sorted union of the inclusive date
    ranges stored in the record, `baseline_ranges` (the method-required baseline days: for Jun-Aug
    12 May..20 Sep of each year 1992..2002, 1,452 days) and `target_days` (1 Jun..31 Aug, 92 days).
    The record keeps ranges and counts only; the S1 file names and S2 time indices below are
    functions of these days."""
    base = np.concatenate([R.target_day_indices(dt.date.fromisoformat(a), dt.date.fromisoformat(b))
                           for a, b in rec["baseline_ranges"]])
    a, b, n = rec["target_days"]
    tgt = R.target_day_indices(dt.date.fromisoformat(a), dt.date.fromisoformat(b))
    for name, d, n_rec in (("baseline_days", base, rec["baseline_days"]), ("target_days", tgt, n)):
        if d.size != n_rec:
            raise ValueError(f"{rec['instance']['instance_id']}: {name} has {d.size} days, record says {n_rec}")
    days = np.union1d(base, tgt)
    if days.size != rec["required_days"]:
        raise ValueError(f"{rec['instance']['instance_id']}: union has {days.size} days, record says {rec['required_days']}")
    return days


def s1_files(rec: dict) -> list[str]:
    """S1 file names (one daily file per required day, `sst_YYYYMMDD.nc`)."""
    return R.s1_files(required_day_indices(rec))


def s2_time_indices(rec: dict) -> list[int]:
    """S2 time indices of the required days; each is one chunk (1, 626, 1051), chunk index (t, 0, 0)."""
    return [int(i) for i in required_day_indices(rec)]
