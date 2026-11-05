"""Where does m90's largest difference to Octave sit, and are there NaN days in that cell's baseline? (one chunk; argv: shard first_column_of_shard chunk_first_column)"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_criterion as dc
from icsa.refdet import core

root = Path(sys.argv[1]); name, ja, col0 = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
k = 2
nc = {"s20": 15, "s21": 15}.get(name, 16)
mm = np.memmap(root / "pack" / "packed.f32", np.float32, "r", shape=(dc.T_DAYS, dc.N_CELLS))
c0 = (col0 - 1) * dc.ROWS
sst = np.array(mm[:, c0:c0 + k * dc.ROWS]).reshape(dc.T_DAYS, k, dc.ROWS)
a = col0 - ja
o90 = np.memmap(root / "shards" / name / "m90.f64", np.float64, "r", shape=(366, nc, dc.ROWS))[:, a:a + k, :]
f = core.climatology(sst, np.arange(dc.T_DAYS), baseline=dc.BASE)[0]
d = np.abs(f - o90)
d[~np.isfinite(d)] = 0
doy, j, i = np.unravel_index(np.argmax(d), d.shape)
cell = c0 + j * dc.ROWS + i
lo, hi = dc.BASE[0] - 5, dc.BASE[1] + 5
x = sst[lo:hi + 1, j, i]
print({"max_abs": float(d[doy, j, i]), "day_of_year_index": int(doy), "packed_cell": int(cell), "baseline_days_with_nan": int(np.isnan(x).sum()),
       "baseline_days": int(x.size), "cells_in_chunk_with_any_baseline_nan": int(np.isnan(sst[lo:hi + 1]).any(0).sum()),
       "cells_at_the_bound": int((d.max(0) >= 3.05e-5).sum())})
