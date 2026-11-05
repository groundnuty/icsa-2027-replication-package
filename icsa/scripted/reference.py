"""SST reference per instance, from the local copy #3 verified bitwise: read through neither the sandbox nor a provider.

A run's `sst_sha256` must equal this, in every option and both layouts: it shows that the path delivered the same
values as the verified data, independently of whether the mask happens to come out equal.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import netCDF4
import numpy as np

from .. import paths
from .insandbox import canonical_sha256, s1_name

S1Z_DIR = paths.DATA_ROOT / "s1z"
FILE = "reference_sst_sha256.json"


def _required_days(rec: dict) -> np.ndarray:
    from ..instances.load import required_day_indices
    return required_day_indices(rec)


def local_sst_sha256(rec: dict, s1z_dir: Path = S1Z_DIR) -> str:
    i = rec["instance"]
    days = _required_days(rec)
    out = np.empty((days.size, i["lat1"] - i["lat0"], i["lon1"] - i["lon0"]), np.float32)
    for k, d in enumerate(days):
        with netCDF4.Dataset(Path(s1z_dir) / s1_name(d)) as ds:
            v = ds["analysed_sst"]
            if v.dimensions[0] != "time" or v.dimensions[1] != "latitude" or v.dimensions[2] != "longitude":
                raise ValueError(f"unexpected dimensions {v.dimensions}")
            out[k] = np.ma.filled(v[0, i["lat0"]:i["lat1"], i["lon0"]:i["lon1"]], np.nan).astype(np.float32)
    return canonical_sha256(out)


def load_or_build_reference(out_dir: Path | str, records: list[dict], s1z_dir: Path = S1Z_DIR) -> dict[str, str]:
    """instance id -> hash; written to `<out_dir>/reference_sst_sha256.json` and reused from it."""
    p = Path(out_dir) / FILE
    have = json.loads(p.read_text()) if p.exists() else {}
    for rec in records:
        iid = rec["instance"]["instance_id"]
        if iid not in have:
            have[iid] = local_sst_sha256(rec, s1z_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(have, indent=1))
    return have
