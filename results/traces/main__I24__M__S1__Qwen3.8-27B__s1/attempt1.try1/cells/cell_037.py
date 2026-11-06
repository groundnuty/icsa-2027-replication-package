import numpy as np, datetime as dt, os
import xarray as xr

OUT = "/work/mhw"
BASE = "/data/icsa2027_data_20261101T090944Z/s1z"
epoch = dt.date(1981,1,1)

z1 = np.load(f"{OUT}/results1.npz")
sea_r = z1["sea_r"].astype(int); sea_c = z1["sea_c"].astype(int)
base = np.concatenate([np.load(f"{OUT}/base_{a:04d}_{b:04d}.npy") for a,b in
                       [(0,500),(500,1000),(1000,1500),(1500,2000),(2000,2500),(2500,3300),(3300,4028)]], axis=0)
base_dates = [dt.date(1991,12,27) + dt.timedelta(days=k) for k in range(4028)]
tgt_dates  = [dt.date(2004,6,1) + dt.timedelta(days=k) for k in range(92)]
date2idx = {d:k for k,d in enumerate(base_dates)}
mlen = [31,29,31,30,31,30,31,31,30,31,30,31]; mcum=[0]+list(np.cumsum(mlen))
def doy(d): return mcum[d.month-1]+d.day
tgt = np.load(f"{OUT}/tgt_0000_0092.npy")

# independent pool builder (different structure: year-first)
md_of_doy = {}
for k in range(366):
    dd = (dt.date(2004,1,1)+dt.timedelta(days=k))
    md_of_doy[doy(dd)] = (dd.month, dd.day)

def pool_dates_indep(dd):
    out = []
    for y in range(1992, 2003):
        a = dt.date(y, *md_of_doy[dd])
        for k in range(-5,6):
            out.append(a + dt.timedelta(days=k))
    return out

def naive_mhw(h):
    # fully naive: scan
    n = len(h); mask = [0]*n
    i = 0; runs = []
    while i < n:
        if h[i]:
            j = i
            while j+1 < n and h[j+1]: j += 1
            if j-i+1 >= 5: runs.append([i,j])
            i = j+1
        else: i += 1
    merged = []
    for r in runs:
        if merged and r[0]-merged[-1][1]-1 <= 2: merged[-1][1] = r[1]
        else: merged.append(r)
    for s,e in merged:
        for x in range(s, e+1): mask[x] = 1
    return mask

import random
random.seed(11)
test_cells = [0, 500, 1238, 2000, 3303]
ok_all = True
for ci in test_cells:
    r, c = sea_r[ci], sea_c[ci]
    # recompute smoothed threshold for each target doy via explicit loops
    thr_smooth = {}
    # raw threshold for all doys first (needed for smoothing)
    raw = {}
    for dd in range(1,367):
        if dd == 60: continue
        vals = []
        for d in pool_dates_indep(dd):
            v = base[date2idx[d], r, c]
            if np.isfinite(v): vals.append(v)
        vals = np.array(vals, dtype=np.float64)
        raw[dd] = np.quantile(vals, 0.9, method="hazen")
    raw[60] = 0.5*(raw[59]+raw[61])
    for dd in range(1,367):
        idxs = [(dd-16+k) % 366 for k in range(31)]  # (dd-15..dd+15) 1-based -> 0-based
        thr_smooth[dd] = np.mean([raw[i+1] for i in idxs])
    # hot days and MHW
    h = []
    for i, d in enumerate(tgt_dates):
        v = tgt[i, r, c]
        th = thr_smooth[doy(d)]
        h.append(bool(np.isfinite(v) and v >= th))
    m = naive_mhw(h)
    # compare with saved
    saved = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf", decode_times=False)["mhw"].values[:, r, c]
    match = all(int(a)==int(b) for a,b in zip(m, saved))
    ok_all &= match
    print(f"cell {ci} (r={r},c={c}): independent mhw={m} matches saved mask: {match}; n_days_mhw={sum(m)}")

# event re-check from saved mask
chk = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
m = chk["mhw"].values
active = m.any(axis=(1,2))
idx = np.flatnonzero(np.diff(np.concatenate(([0], active.view(np.int8), [0]))==1))
ends = np.flatnonzero(np.diff(np.concatenate(([0], active.view(np.int8), [0]))==-1))-1
for s,e in zip(idx, ends):
    print("event from saved mask:", tgt_dates[s], "->", tgt_dates[e])
print("ALL INDEPENDENT CHECKS PASS:", ok_all)
