"""Check the packed S1 cells against part 1's block inputs, byte for byte.

    python3 verify_pack.py <pack dir> <part-1 root> <block> [<block> ...]

Each part-1 block (make_input.py: S1 values of an h x w box over the days first..last, float32, Fortran order (lat, lon, time), with
the sha256 of the exact bytes in source.json) is cut to the cells that lie in BALarea; the same cells over the same days
are read from packed.f32, and the two arrays must be identical bit for bit (NaN where NaN). Part 1 read S1 from
`s1/`; the pack comes from the master copy `s1z/`, so this is what ties the two together, and the cell order.
"""
import json
import sys
from pathlib import Path

import numpy as np

pack, root, blocks = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
cells = np.fromfile(pack / "cells.i32", np.int32).reshape(-1, 2)
N, T = len(cells), 15340
mm = np.memmap(pack / "packed.f32", np.float32, "r", shape=(T, N))
out = []
for b in blocks:
    h, w, Tb, first, lat0, lon0, *_ = (int(v) for v in (root / b / "in" / "meta.txt").read_text().split())
    import datetime as dt
    d0 = (dt.date(first // 10000, first // 100 % 100, first % 100) - dt.date(1982, 1, 1)).days
    blk = np.fromfile(root / b / "in" / "sst.bin", np.float32).reshape((h, w, Tb), order="F")
    k = np.nonzero((cells[:, 0] >= lat0) & (cells[:, 0] < lat0 + h) & (cells[:, 1] >= lon0) & (cells[:, 1] < lon0 + w))[0]
    a = np.array(mm[d0:d0 + Tb][:, k])                                  # (Tb, ncells)
    c = blk[cells[k, 0] - lat0, cells[k, 1] - lon0, :].T                # (Tb, ncells)
    same = bool(np.array_equal(a.view(np.uint32), c.view(np.uint32)) or (np.array_equal(np.isnan(a), np.isnan(c)) and np.array_equal(a[~np.isnan(a)], c[~np.isnan(c)])))
    src = json.loads((root / b / "in" / "source.json").read_text())
    rec = {"block": b, "box": [lat0, lat0 + h, lon0, lon0 + w], "days": Tb, "first_day_index": d0, "balarea_cells_in_box": int(k.size),
           "cells_in_box": h * w, "values_compared": int(a.size), "nan_values_in_pack": int(np.isnan(a).sum()),
           "bit_identical": same, "block_input_sha256": src["sst_sha256"]}
    out.append(rec)
    print(json.dumps(rec), flush=True)
sys.exit(0 if all(r["bit_identical"] for r in out) else 1)
