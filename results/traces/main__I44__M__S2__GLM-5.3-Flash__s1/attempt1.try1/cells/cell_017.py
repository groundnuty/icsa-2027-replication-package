import numpy as np, time, pickle
from datetime import date, timedelta
from collections import defaultdict

block = np.load("/tmp/sst_block.npy")
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")
nb = 4028
base = block[:nb].astype(np.float64)

idx_of = {s: i for i, s in enumerate(alldays)}
cum_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_of_date(dt): return cum_before[dt.month-1] + dt.day

baseline_dates = [date(1992,1,1)+timedelta(days=i) for i in range((date(2002,12,31)-date(1992,1,1)).days+1)]
anchors = defaultdict(list)
for b in baseline_dates: anchors[doy_of_date(b)].append(b)

pool_masks = {}
for d in range(1, 367):
    if d == 60: continue
    mask = np.zeros(nb, dtype=bool)
    for b in anchors[d]:
        o = b.toordinal()
        for off in range(-5, 6):
            i = idx_of.get(date.fromordinal(o+off).isoformat())
            if i is not None: mask[i] = True
    pool_masks[d] = mask
sizes = [pool_masks[d].sum() for d in range(1,367) if d != 60]
print("pool sizes min/max:", min(sizes), max(sizes))
with open("/tmp/pools.pkl","wb") as fh: pickle.dump(pool_masks, fh)

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
    j = np.floor(h).astype(int); g = h - j
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
    vals = base[pool_masks[d]]
    fin = np.isfinite(vals)
    cnt = fin.sum(axis=0)
    ssum = np.where(fin, vals, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw_clim[d-1] = ssum / cnt
    raw_thr[d-1] = hazen_nanperc(vals, 0.9)
print("raw pools recomputed:", round(time.time()-t0,1), "s")

for arr in (raw_thr, raw_clim):
    arr[59] = (arr[58] + arr[60]) / 2.0

mincnt = min(np.isfinite(base[pool_masks[d]]).sum(axis=0)[sea_cells].min() for d in range(1,367) if d != 60)
print("min finite count over sea cells & pools:", mincnt)

import warnings
vals = base[pool_masks[153]]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ref = np.nanpercentile(vals, 90, axis=0, method="hazen")
print("hazen cross-check max diff (doy153):", np.nanmax(np.abs(raw_thr[152] - ref)))

def smooth31(raw):
    acc = np.zeros_like(raw)
    for off in range(-15, 16):
        acc += np.roll(raw, off, axis=0)
    return acc / 31.0

thr = smooth31(raw_thr); clim = smooth31(raw_clim)
print("thr doy180 mean sea:", np.nanmean(thr[179][sea_cells]), "clim doy180 mean sea:", np.nanmean(clim[179][sea_cells]))
print("nan thr:", np.isnan(thr).sum(), "nan clim:", np.isnan(clim).sum())
np.save("/tmp/thr_smooth.npy", thr)
np.save("/tmp/clim_smooth.npy", clim)
np.save("/tmp/raw_thr.npy", raw_thr); np.save("/tmp/raw_clim.npy", raw_clim)
