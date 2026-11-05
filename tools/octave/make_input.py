"""Write one Octave equivalence block: SST for an h x w block of cells from 1991-12-27 (baseline
1992-2002 plus its 5 padding days, as Step_2 passes the full record) to the end of the target years,
float32 in Fortran order (lat, lon, time), with meta.txt for run_block.m and source.json.

    uv run python tools/octave/make_input.py <block dir> <lat0> <lon0> <h> <w> <first target year> <last target year> [s1|raw]

source s1 (default): the daily S1 files the agents read. raw: the yearly download read as MATLAB
ncread does (fill value only; out-of-range values kept).
"""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from icsa import grid, paths
from icsa.extent import CellBox
from icsa.refdet import load_sst
from icsa.refdet import validate as V

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
lat0, lon0, h, w, y0, y1 = (int(x) for x in sys.argv[2:8])
source = sys.argv[8] if len(sys.argv) > 8 else "s1"
first = min(dt.date(1991, 12, 27), dt.date(y0, 1, 1))
cs, ce = dt.date(1992, 1, 1), dt.date(2002, 12, 31)
ms, me = max(dt.date(y0, 1, 1), dt.date(1982, 1, 2)), min(dt.date(y1, 12, 31), dt.date(2023, 12, 30))
days = np.arange(grid.day_index(first), grid.day_index(max(me, dt.date(2003, 1, 5))) + 1)
box = CellBox(lat0, lat0 + h, lon0, lon0 + w)
if source == "s1":
    sst = load_sst(box, days, "s1")
elif source == "raw":
    V.VALID_RANGE = False
    sst = V.read_band(V.raw_index(paths.RAW), days, lat0, lat0 + h)[:, :, lon0:lon0 + w]
else:
    raise SystemExit(f"unknown source {source}")
sst = np.ascontiguousarray(sst, np.float32)
blob = sst.transpose(1, 2, 0).ravel(order="F").tobytes()   # Octave reads [h w T] column-major
(out / "sst.bin").write_bytes(blob)
ymd = lambda d: d.year * 10000 + d.month * 100 + d.day
(out / "meta.txt").write_text(f"{h} {w} {days.size} {ymd(first)} {lat0} {lon0} {ymd(cs)} {ymd(ce)} {ymd(ms)} {ymd(me)}\n")
fin = np.isfinite(sst)
info = {"source": source, "box": [lat0, lat0 + h, lon0, lon0 + w], "first_day": first.isoformat(),
        "n_days": int(days.size), "baseline": [cs.isoformat(), ce.isoformat()],
        "detection": [ms.isoformat(), me.isoformat()], "sst_sha256": hashlib.sha256(blob).hexdigest(),
        "cells_finite_any": int(fin.any(0).sum()), "cells_finite_all": int(fin.all(0).sum()),
        "cells_intermittent_nan": int((fin.any(0) & ~fin.all(0)).sum()),
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
(out / "source.json").write_text(json.dumps(info, indent=1))
print(json.dumps(info))
