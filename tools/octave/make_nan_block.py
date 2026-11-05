"""Copy an equivalence block's input and inject NaN deterministically, so the Octave equivalence also
covers the NaN paths that real 202506 baseline data never exercise (every S1 cell is either always
finite or always NaN in 1992-2002). Counterfactual runs on partial data take exactly these paths.

    uv run python tools/octave/make_nan_block.py <source block dir> <new block dir> [seed]

Rows of the 30 x 30 block (others unchanged):
  0-4    10 % of all days NaN at random                         quantile/mean on pools of varying size
  5-7    1 Feb..31 Mar NaN in every year                        all-NaN day-of-year pools -> smoothing omitnan
  8-9    23 Feb..5 Mar NaN in every year                        28 Feb pool all NaN, 1 Mar not: day 60 omitnan mean
  10-12  10 % of target-period days NaN at random               detection with missing target days
  13-14  only 40 random baseline-period days finite             pools of 0, 1, 2 values (one-value duplication, clamp)
"""
import datetime as dt
import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np

from icsa import grid

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
seed = int(sys.argv[3]) if len(sys.argv) > 3 else 0
rng = np.random.default_rng(seed)
(dst / "in").mkdir(parents=True, exist_ok=True)
h, w, T, first, lat0, lon0, cs, ce, ms, me = (int(v) for v in (src / "in" / "meta.txt").read_text().split())
ymd = lambda v: grid.day_index(dt.date(v // 10000, v // 100 % 100, v % 100))
d0 = ymd(first)
days = np.arange(d0, d0 + T)
dates = [grid.day_date(int(i)) for i in days]
md = np.array([(d.month, d.day) for d in dates])
sst = np.fromfile(src / "in" / "sst.bin", np.float32).reshape((h, w, T), order="F").copy()  # (h, w, T)

sst[0:5][rng.random((5, w, T)) < 0.10] = np.nan
febmar = (md[:, 0] == 2) | (md[:, 0] == 3)
sst[5:8, :, febmar] = np.nan
late_feb = ((md[:, 0] == 2) & (md[:, 1] >= 23)) | ((md[:, 0] == 3) & (md[:, 1] <= 5))
sst[8:10, :, late_feb] = np.nan
target = (days >= ymd(ms)) & (days <= ymd(me))
m = rng.random((3, w, T)) < 0.10
m &= target[None, None, :]
sst[10:13][m] = np.nan
base_pad = (days >= ymd(cs) - 5) & (days <= ymd(ce) + 5)
keep = np.zeros((2, w, T), bool)
idx = np.nonzero(base_pad)[0]
for j in range(2):
    for i in range(w):
        keep[j, i, rng.choice(idx, 40, replace=False)] = True
sst[13:15][~keep] = np.nan

blob = sst.ravel(order="F").tobytes()
(dst / "in" / "sst.bin").write_bytes(blob)
shutil.copy(src / "in" / "meta.txt", dst / "in" / "meta.txt")
fin = np.isfinite(sst)
info = json.loads((src / "in" / "source.json").read_text())
info.update({"derived_from": str(src), "nan_injection_seed": seed, "nan_recipe": __doc__.split("Rows of")[1].strip(),
             "sst_sha256": hashlib.sha256(blob).hexdigest(),
             "cells_finite_any": int(fin.any(2).sum()), "cells_finite_all": int(fin.all(2).sum()),
             "cells_intermittent_nan": int((fin.any(2) & ~fin.all(2)).sum()),
             "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
(dst / "in" / "source.json").write_text(json.dumps(info, indent=1))
print({k: info[k] for k in ("cells_finite_any", "cells_finite_all", "cells_intermittent_nan", "sst_sha256")})
