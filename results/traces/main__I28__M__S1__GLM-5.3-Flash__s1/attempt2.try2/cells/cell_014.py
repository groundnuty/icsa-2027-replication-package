import numpy as np, json
work = "/work"
thr = np.load(work+"/thr_raw.npy"); thr_s = np.load(work+"/thr_s.npy")
clim = np.load(work+"/clim_raw.npy"); clim_s = np.load(work+"/clim_s.npy")
tf = np.load(work+"/target_finite.npy")
rows, cols = np.where(tf)

# smoothing check restricted to sea cells
d0 = 200
manual = np.mean([thr[(d0-15+j) % 366] for j in range(31)], axis=0)
print("smooth check day200 maxdiff (sea):", np.nanmax(np.abs(manual - thr_s[d0-1])[tf]))
print("land cells NaN in thr_s:", np.isnan(thr_s[:, ~tf]).all(), "| in clim_s:", np.isnan(clim_s[:, ~tf]).all())

# scalar reference hazen check on random (cell, doy) using independent code path
import datetime as dt
blocks = sorted(os.listdir(work+"/cache")) if False else None
import os
parts = [np.load(os.path.join(work,"cache",b), mmap_mode="r") for b in sorted(os.listdir(work+"/cache"))]
data32 = np.concatenate(parts, axis=0)
start = dt.date(1991,12,27)
dates = [start + dt.timedelta(days=i) for i in range(data32.shape[0])]
cand = [i for i,d in enumerate(dates) if (dt.date(1992,1,1) <= d <= dt.date(2002,12,31)) or d <= dt.date(1991,12,31) or (dt.date(2003,1,1) <= d <= dt.date(2003,1,5))]
def in_pool(test, d): return -5 <= test.timetuple().tm_yday - d <= 5

def hazen_scalar(v, q=0.9):
    x = np.sort(v[~np.isnan(v)])
    n = x.size
    if n == 0: return np.nan
    if n == 1: return float(x[0])
    h = (n-1)*q + 1
    lo, hi = int(np.floor(h)), int(np.ceil(h))
    return float(x[lo-1] + (h-lo)*(x[hi-1]-x[lo-1]))

rng = np.random.default_rng(42)
ok_thr, ok_clim = True, True
for trial in range(12):
    r, c = rng.choice(rows), rng.choice(cols)
    d = int(rng.choice([1, 2, 59, 61, 180, 240, 300, 365, 366]))
    if d == 60: d = 59
    idx = [i for i in cand if in_pool(dates[i], d)]
    v = np.array([data32[i, r, c] for i in idx], dtype=np.float64).astype(np.float64)  # raw float32 -> f64
    ref_t, ref_c = hazen_scalar(v), np.nanmean(v)
    if not np.isclose(ref_t, thr[d-1, r, c], rtol=0, atol=1e-9): ok_thr = False; print("THR mismatch", r, c, d, ref_t, thr[d-1,r,c])
    if not np.isclose(ref_c, clim[d-1, r, c], rtol=0, atol=1e-9): ok_clim = False; print("CLIM mismatch", r, c, d, ref_c, clim[d-1,r,c])
print("scalar hazen/mean checks pass:", ok_thr, ok_clim)
del data32, parts
