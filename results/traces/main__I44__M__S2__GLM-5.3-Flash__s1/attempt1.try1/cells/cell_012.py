import numpy as np, time
from datetime import date, timedelta

block = np.load("/tmp/sst_block.npy")           # (4120, 60, 60) float32
alldays = open("/tmp/alldays.txt").read().split("\n")
sea_cells = np.load("/tmp/sea_cells.npy")        # (60, 60) bool
nb = 4028                                        # baseline days 1991-12-27..2003-01-05
base = block[:nb].astype(np.float64)             # baseline in float64
print("base", base.shape, base.dtype)

# day-of-year mapping (month/day based, 1..366, Feb29=60)
cum = [0,31,59,90,120,151,181,212,243,273,304,334]  # days before month (non-leap); Feb29 handled specially
def doy_of(s):
    y,m,d = int(s[:4]), int(s[5:7]), int(s[8:10])
    if m == 2 and d == 29: return 60
    return cum[m-1] + d
doy = np.array([doy_of(s) for s in alldays[:nb]])
print("doy range", doy.min(), doy.max(), "n doy60:", (doy==60).sum())

# pool membership: for each used doy d (1..366, d != 60), dates with mod-366 |doy-d| <= 5
pools = {}
for d in range(1, 367):
    if d == 60: continue
    dist = np.abs(doy - d)
    dist = np.minimum(dist, 366 - dist)
    sel = (doy != 60) & (dist <= 5)
    pools[d] = sel
cnt_pool = np.array([pools[d].sum() for d in range(1,367) if d != 60])
print("pool sizes: min", cnt_pool.min(), "max", cnt_pool.max())

def hazen_nanperc(A, p=0.9):
    # A: (n, ...) ; type 5: h = n*p + 0.5 (1-based), linear interpolation
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
    j = np.floor(h).astype(int)          # 1-based
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
    vals = base[pools[d]]                      # (K, 60, 60) float64
    fin = np.isfinite(vals)
    cnt = fin.sum(axis=0)
    ssum = np.where(fin, vals, 0.0).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        raw_clim[d-1] = ssum / cnt
    raw_thr[d-1] = hazen_nanperc(vals, 0.9)
print("raw pools done", time.time()-t0, "s")

# day 60 = mean of day 59 and day 61 (index 58 and 60)
for arr in (raw_thr, raw_clim):
    arr[59] = (arr[58] + arr[60]) / 2.0
print("day60 filled, nan count thr:", np.isnan(raw_thr).sum(), "clim:", np.isnan(raw_clim).sum())

# check every sea cell has cnt>=1 in every pool
mincnt = None
for d in range(1,367):
    if d == 60: continue
    c = np.isfinite(base[pools[d]]).sum(axis=0)
    m = c[sea_cells].min()
    mincnt = m if mincnt is None else min(mincnt, m)
print("min finite count over sea cells & pools:", mincnt)

# cross-check hazen vs numpy on one doy
import warnings
vals = base[pools[200]]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    ref = np.nanpercentile(vals, 90, axis=0, method="hazen")
print("hazen cross-check max diff:", np.nanmax(np.abs(raw_thr[199] - ref)))

# smoothing: unweighted centred 31-day moving mean, wraps mod 366
def smooth31(raw):
    out = np.empty_like(raw)
    offs = np.arange(-15, 16)
    acc = np.zeros_like(raw)
    for off in offs:
        acc += np.roll(raw, off, axis=0)
    out[:] = acc / 31.0
    return out

t0=time.time()
thr = smooth31(raw_thr)
clim = smooth31(raw_clim)
print("smoothing done", time.time()-t0, "s")
print("thr sample doy180 mean over sea cells:", np.nanmean(thr[179][sea_cells]))
print("clim sample doy180 mean over sea cells:", np.nanmean(clim[179][sea_cells]))
print("nan in thr:", np.isnan(thr).sum(), "nan in clim:", np.isnan(clim).sum())
np.save("/tmp/thr_smooth.npy", thr)
np.save("/tmp/clim_smooth.npy", clim)
