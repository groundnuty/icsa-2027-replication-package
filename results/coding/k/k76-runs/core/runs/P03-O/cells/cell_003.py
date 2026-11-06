import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
TOL = 1e-4

def hazen(vals, p):
    v = sorted(x for x in vals if x == x)
    n = len(v)
    if n == 0:
        return float("nan")
    h = n * p + 0.5
    if h <= 1:
        return v[0]
    if h >= n:
        return v[-1]
    f = int(h)
    return v[f - 1] + (h - f) * (v[f] - v[f - 1])

def doy366(d):
    n = d.timetuple().tm_yday
    if not calendar.isleap(d.year) and n > 59:
        n += 1
    return n

import math
W = 3
cube = np.load("cube.npy").tolist()
tgt = np.load("target.npy").tolist()
meta = json.load(open("meta.json"))
tdays = [dt.date.fromisoformat(s) for s in meta["days"]]
nY = len(cube); nlat = len(cube[0][0]); nlon = len(cube[0][0][0])
ndays = len(tdays)
cells = [(r, c) for r in range(nlat) for c in range(nlon)
         if all(math.isfinite(tgt[k][r][c]) for k in range(ndays))]
print("sea cells", len(cells), "years", nY, "pool half-width", W)
tdoy = [doy366(d) for d in tdays]
nan = float("nan")
thr_rows = []
clim_rows = []
for n, (r, c) in enumerate(cells):
    raw_t = [nan] * 366
    raw_c = [nan] * 366
    for d in range(138, 260):
        i = d - 133
        pool = [cube[iy][j][r][c] for iy in range(nY) for j in range(i - W, i + W + 1)]
        raw_t[d - 1] = hazen(pool, 0.9)
        good = [x for x in pool if x == x]
        raw_c[d - 1] = sum(good) / len(good)
    raw_t[59] = 0.5 * (raw_t[58] + raw_t[60])
    raw_c[59] = 0.5 * (raw_c[58] + raw_c[60])
    row_t = []
    row_c = []
    for d in tdoy:
        row_t.append(sum(raw_t[(d - 1 + off) % 366] for off in range(-15, 16)) / 31)
        row_c.append(sum(raw_c[(d - 1 + off) % 366] for off in range(-15, 16)) / 31)
    thr_rows.append(row_t)
    clim_rows.append(row_c)
    if n % 500 == 0:
        print("cell", n, "of", len(cells), "thr day 1", round(row_t[0], 3))
np.save("cells.npy", np.array(cells))
np.save("thr_t.npy", np.array(thr_rows))
np.save("clim_t.npy", np.array(clim_rows))
print("thresholds", len(thr_rows), "x", len(thr_rows[0]))
