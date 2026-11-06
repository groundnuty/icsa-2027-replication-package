import os, json, calendar, datetime as dt
import numpy as np
import xarray as xr

LAT_MIN, LAT_MAX = 54.81, 56.01
LON_MIN, LON_MAX = 19.61, 20.81
T_START = dt.date(2007, 6, 1)
T_END = dt.date(2007, 8, 31)
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

thr = np.full((366, nC), np.nan)
clim = np.full((366, nC), np.nan)
for d in range(138, 260):
    i = d - 133 - 0
    pool = base[:, i - 5:i + 5 + 1, :].reshape(-1, nC)
    thr[d - 1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
    clim[d - 1] = np.nanmean(pool, axis=0)
thr[59] = 0.5 * (thr[58] + thr[60])
clim[59] = 0.5 * (clim[58] + clim[60])

from scipy.ndimage import uniform_filter1d
thr_s = uniform_filter1d(np.nan_to_num(thr, nan=0.0), 31, axis=0, mode="wrap")
clim_s = uniform_filter1d(np.nan_to_num(clim, nan=0.0), 31, axis=0, mode="wrap")

tdoy = np.array([doy366(d) for d in tdays])
thr_t = thr_s[tdoy - 1]
clim_t = clim_s[tdoy - 1]
print("thresholds", thr_t.shape, "NaN", int(np.isnan(thr_t).sum()))
print("threshold K mean/min/max", round(float(np.nanmean(thr_t)), 3), round(float(np.nanmin(thr_t)), 3), round(float(np.nanmax(thr_t)), 3))
np.save("thr_t.npy", thr_t)
np.save("clim_t.npy", clim_t)
