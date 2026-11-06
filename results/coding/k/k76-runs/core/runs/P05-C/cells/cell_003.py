import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
T_START = dt.date(2003, 6, 1)
T_END = dt.date(2003, 8, 31)
TOL = 1e-4

def doy366(d):
    n = d.timetuple().tm_yday
    if not calendar.isleap(d.year) and n > 59:
        n += 1
    return n

def smooth(x):
    out = np.zeros_like(x)
    for k in range(-15, 16):
        out += np.roll(x, -k, axis=0)
    return out / 31.0

base = np.load("base_s.npy")
meta = json.load(open("meta.json"))
tdays = [dt.date.fromisoformat(s) for s in meta["days"]]
nY, nD, nC = base.shape
print("baseline cube", base.shape)
thr_l = [[None] * nC for _ in range(366)]
clim_l = [[None] * nC for _ in range(366)]
for d in range(138, 260):
    i = d - 133
    pool = base[:, i - 5:i + 6, :].reshape(-1, nC)
    for c in range(nC):
        thr_l[d - 1][c] = np.nanpercentile(pool[:, c], 90, method="hazen")
        clim_l[d - 1][c] = np.nanmean(pool[:, c])
    if d % 20 == 0:
        print("doy", d, "done")
thr = np.array(thr_l, dtype=np.float64)
clim = np.array(clim_l, dtype=np.float64)
thr[59] = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

thr_s = smooth(thr)
clim_s = smooth(clim)
tdoy = np.array([doy366(d) for d in tdays])
thr_t = thr_s[tdoy - 1]
clim_t = clim_s[tdoy - 1]
print("thresholds", thr_t.shape, "NaN", int(np.isnan(thr_t).sum()))
print("threshold K mean/min/max", round(float(thr_t.mean()), 3), round(float(thr_t.min()), 3), round(float(thr_t.max()), 3))
print("climatology K mean", round(float(clim_t.mean()), 3))
np.save("thr_t.npy", thr_t)
np.save("clim_t.npy", clim_t)
