import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 64.51, 65.71
LON_MIN, LON_MAX = 21.97, 23.17
T_START = dt.date(2019, 6, 1)
T_END = dt.date(2019, 8, 31)
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

data = np.load("sst_all.npy")
meta = json.load(open("meta.json"))
nb = meta["nb"]
nY = len(meta["years"])
tdays = [dt.date.fromisoformat(s) for s in meta["days"]]
nlat, nlon = data.shape[1:]
sea = np.isfinite(data[nb:]).all(axis=0)
cells = [(r, c) for r in range(nlat) for c in range(nlon) if sea[r, c]]
print("sea cells", len(cells), "years", nY)
tdoy = [doy366(d) for d in tdays]
nan = float("nan")
thr_rows = []
clim_rows = []
for n, (r, c) in enumerate(cells):
    ser = data[:nb, r, c].tolist()
    raw_t = [nan] * 366
    raw_c = [nan] * 366
    for d in range(138, 260):
        i = d - 133
        pool = []
        for iy in range(nY):
            for j in range(i - 5, i + 6):
                pool.append(ser[iy * 132 + j])
        raw_t[d - 1] = hazen(pool, 0.9)
        good = [x for x in pool if x == x]
        raw_c[d - 1] = sum(good) / len(good)
    raw_t[59] = 0.5 * (raw_t[58] + raw_t[60])
    raw_c[59] = 0.5 * (raw_c[58] + raw_c[60])
    row_t = []
    row_c = []
    for d in tdoy:
        st = 0.0
        sc = 0.0
        for off in range(-15, 16):
            st += raw_t[(d - 1 + off) % 366]
            sc += raw_c[(d - 1 + off) % 366]
        row_t.append(st / 31)
        row_c.append(sc / 31)
    thr_rows.append(row_t)
    clim_rows.append(row_c)
    if n % 500 == 0:
        print("cell", n, "of", len(cells), "thr day 1", round(row_t[0], 3))
np.save("cells.npy", np.array(cells))
np.save("thr_t.npy", np.array(thr_rows))
np.save("clim_t.npy", np.array(clim_rows))
print("thresholds", len(thr_rows), "x", len(thr_rows[0]))
