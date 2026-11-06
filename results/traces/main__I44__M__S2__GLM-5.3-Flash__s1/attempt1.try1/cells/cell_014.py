import numpy as np, time
from datetime import date, timedelta

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
nb = 4028
base = block[:nb].astype(np.float64)

# CORRECT month/day mapping: all years counted leap-style; Feb29=60; Dec31=366
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of(s):
    m, d = int(s[5:7]), int(s[8:10])
    return cum_before[m-1] + d
# sanity checks
tests = {"2004-01-01":1, "2004-02-28":59, "2004-02-29":60, "2004-03-01":61,
         "1999-12-31":366, "2004-06-01":153, "2004-08-31":244, "1993-02-28":59, "1993-03-01":61}
for k, v in tests.items():
    got = doy_of(k)
    assert got == v, (k, got, v)
print("mapping checks pass")

doy = np.array([doy_of(s) for s in alldays[:nb]])
print("baseline doy range", doy.min(), doy.max(), "n doy60 (Feb29):", (doy==60).sum())

pools = {}
for d in range(1, 367):
    if d == 60: continue
    dist = np.abs(doy - d)
    dist = np.minimum(dist, 366 - dist)
    pools[d] = (doy != 60) & (dist <= 5)
cnt_pool = np.array([pools[d].sum() for d in range(1,367) if d != 60])
print("pool sizes: min", cnt_pool.min(), "max", cnt_pool.max())
# check window content for an example: d=153 (Jun 1)
sel = pools[153]
ex = sorted({(alldays[i][:7]) for i in np.flatnonzero(sel)})
print("months in pool of doy 153:", ex)

def hazen_nanperc(A, p=0.9):
    n = A.shape[0]
    flat = A.reshape(n, -1)
    s = np.sort(flat, axis=0)
    m = np.isnan(s).sum(axis=0)
    k = n - m
    out = np.full(flat.shape[1:], np.nan)
    ok = k > 0
    if not ok.any(): return out.reshape(A.shape[1:])
    kk = np.where(ok, k, 1).astype(float)
    h = kk * p + 0.5
    j = np.floor(h).astype(int)
    g = h - j
    j0 = np.clip(j, 1, kk.astype(int)) - 1
    jp = np.clip(j + 1, 1, kk.astype(int)) - 1
    idx = np.arange(flat.shape[1])
    res = s[j0, idx] + g * (s[jp, idx] - s[j0, idx])
    out[ok] = res[ok]
    return out.reshape(A.shape[1:])

t0 = time.time()
raw_thr = np.full((366, 60, 60), np.nan)
raw_clim = np.full((366, 60, 60), np.nan)
for d in range(1, 367):
    if d == 60: continue
    vals = base[pools[d]]
    fin = np.isfinite(vals)
    cnt = fin.sum(axis=0)
    ssum = np.where(fin, vals, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw_clim[d-1] = ssum / cnt
    raw_thr[d-1] = hazen_nanperc(vals, 0.9)
print("raw pools done", time.time()-t0, "s")

for arr in (raw_thr, raw_clim):
    arr[59] = (arr[58] + arr[60]) / 2.0
print("day60 done; nan thr:", np.isnan(raw_thr).sum(), "nan clim:", np.isnan(raw_clim).sum())

# min finite count over sea cells for every pool
mincnt = min(np.isfinite(base[pools[d]]).sum(axis=0)[sea_cells].min() for d in range(1,367) if d != 60)
print("min finite count over sea cells & pools:", mincnt)

import warnings
vals = base[pools[153]]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ref = np.nanpercentile(vals, 90, axis=0, method="hazen")
print("hazen cross-check max diff:", np.nanmax(np.abs(raw_thr[152] - ref)))
# Feb29 values included in neighbours: verify count of doy-60 baseline days
print("baseline Feb29 dates:", [alldays[i] for i in np.flatnonzero(doy==60)])

def smooth31(raw):
    acc = np.zeros_like(raw)
    for off in range(-15, 16):
        acc += np.roll(raw, off, axis=0)
    return acc / 31.0

t0=time.time()
thr = smooth31(raw_thr)
clim = smooth31(raw_clim)
print("smoothing done", time.time()-t0, "s")
print("thr doy180 mean sea:", np.nanmean(thr[179][sea_cells]), "clim doy180 mean sea:", np.nanmean(clim[179][sea_cells]))
print("nan thr:", np.isnan(thr).sum(), "nan clim:", np.isnan(clim).sum())
np.save("/tmp/thr_smooth.npy", thr)
np.save("/tmp/clim_smooth.npy", clim)
