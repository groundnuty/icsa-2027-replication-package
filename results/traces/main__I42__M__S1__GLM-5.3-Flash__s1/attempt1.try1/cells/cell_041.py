import numpy as np, pickle, h5py, time
from datetime import date, timedelta

base = "/data/icsa2027_data_20261101T090944Z/s1z"
arr = np.load("/work/baseline_region_corr.npy").astype(np.float64)
N = arr.shape[0]
d0 = date(1991,12,27)
date_list = [d0 + timedelta(days=k) for k in range(N)]
k_of = {d: k for k, d in enumerate(date_list)}

MD_CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy_md(dt): return MD_CUM[dt.month-1] + dt.day

base_dates = [d for d in date_list if date(1992,1,1) <= d <= date(2002,12,31)]

# calendar-window pools (d=1..366, skip 60)
pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    win = set()
    for b in base_dates:
        if doy_md(b) == d:
            k = k_of[b]
            for kk in range(max(0,k-5), min(N, k+6)):
                win.add(kk)
    pool_idx[d] = sorted(win)
sizes = {d: len(v) for d, v in pool_idx.items()}
import collections
print("pool sizes:", collections.Counter(sizes.values()))
print("d=1:", date_list[pool_idx[1][0]], date_list[pool_idx[1][-1]], sizes[1])
print("d=366:", date_list[pool_idx[366][0]], date_list[pool_idx[366][-1]], sizes[366])
print("d=59 Feb29 count:", sum(1 for k in pool_idx[59] if date_list[k].month==2 and date_list[k].day==29))
with open("/work/pool_idx_corr.pkl","wb") as f:
    pickle.dump(pool_idx, f)

# thresholds and climatology (hazen 90th pct, mean)
thr = np.full((366, 60, 60), np.nan)
clim = np.full((366, 60, 60), np.nan)
t0 = time.time()
for d in range(1, 367):
    if d == 60: continue
    v = arr[pool_idx[d]]
    clim[d-1] = np.nanmean(v, axis=0)
    s = np.sort(v, axis=0)
    nn = np.sum(~np.isnan(v), axis=0)
    with np.errstate(invalid="ignore"):
        h = nn * 0.9 + 0.5
    h = np.where(nn > 0, h, np.nan)
    fl = np.floor(h)
    frac = h - fl
    lo_c = np.clip(fl.astype(np.int64)-1, 0, v.shape[0]-1)
    hi_c = np.clip(fl.astype(np.int64), 0, v.shape[0]-1)
    v_lo = np.take_along_axis(s, lo_c[None], axis=0)[0]
    v_hi = np.take_along_axis(s, hi_c[None], axis=0)[0]
    q = v_lo + frac*(v_hi-v_lo)
    thr[d-1] = np.where(nn > 0, q, np.nan)
print("thr/clim compute:", round(time.time()-t0,1), "s")

with np.errstate(invalid="ignore"):
    thr[59] = (thr[58] + thr[60]) / 2.0
    clim[59] = (clim[58] + clim[60]) / 2.0

def smooth_circ(a):
    s = np.zeros_like(a)
    for k in range(-15, 16):
        s += np.roll(a, -k, axis=0)
    return s / 31.0

thr_s = smooth_circ(thr)
clim_s = smooth_circ(clim)
np.save("/work/thr_smooth_corr.npy", thr_s)
np.save("/work/clim_smooth_corr.npy", clim_s)
print("land cells:", (~np.isfinite(thr_s).all(axis=0)).sum())
print("saved corrected arrays")
