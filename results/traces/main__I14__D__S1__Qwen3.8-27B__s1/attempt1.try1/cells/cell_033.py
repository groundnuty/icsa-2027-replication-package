import numpy as np, time, warnings
from datetime import date, timedelta

t0 = time.time()
B = np.load('/work/data/B.npy')          # (4028, 60, 60), 1991-12-27 .. 2003-01-05
T = np.load('/work/data/T.npy')          # (92, 60, 60)
si = np.load('/work/data/sea_idx.npy')
nsea = len(si)

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)
def doy_of(m, d):
    return d + (int(ENDS[m-2]) if m >= 2 else 0)

d0 = date(1991,12,27)
sea_mask = np.zeros(3600, bool); sea_mask[si] = True
r3 = np.where(sea_mask)[0]
Bsea = B[:, r3//60, r3%60]   # (4028, nsea)

def pool_rows(d):
    m, dd = md_of(d)
    rows = []
    for y in range(1992, 2003):
        c = date(y, m, dd)
        for k in range(-5, 6):
            rows.append((c + timedelta(days=k) - d0).days)
    return np.array(rows, dtype=int)

# brute force (independent definition)
base_dates = []
d = date(1992,1,1)
while d <= date(2002,12,31):
    base_dates.append(d); d += timedelta(days=1)
def pool_rows_bruteforce(d):
    s = set()
    for b in base_dates:
        if doy_of(b.month, b.day) == d:
            for k in range(-5, 6):
                s.add((b + timedelta(days=k) - d0).days)
    return np.array(sorted(s), dtype=int)

# verify row sets for all d
for d in list(range(1, 367)):
    if d == 60: continue
    assert np.array_equal(pool_rows(d), pool_rows_bruteforce(d)), d
print("pool row sets verified for all 365 doys (vs independent brute force)")

def hazen_vec(pool, p=0.9):
    m = pool.shape[1]
    nvalid = np.sum(np.isfinite(pool), axis=0)
    out = np.full(m, np.nan)
    ok = nvalid >= 9
    if ok.any():
        x = np.where(np.isfinite(pool), pool, np.inf)
        xs = np.sort(x, axis=0)
        nv = nvalid[ok].astype(float)
        h = (nv + 1.0) * p
        lo = np.floor(h).astype(int)
        f = h - lo
        cols = np.arange(m)[ok]
        out[ok] = xs[lo-1, cols] + f * (xs[lo, cols] - xs[lo-1, cols])
    small = nvalid[(nvalid >= 1) & (nvalid < 9)]
    for c in np.where((nvalid >= 1) & (nvalid < 9))[0]:
        col = pool[np.isfinite(pool[:, c]), c]
        n = len(col); h = (n+1)*p
        if h <= n:
            lo = int(np.floor(h)); f = h - lo
            cs = np.sort(col)
            out[c] = cs[lo-1] + f*(cs[lo]-cs[lo-1]) if lo < n else cs[n-1]
        else:
            out[c] = np.sort(col)[-1]   # clamp like numpy
    return out

def hazen_naive(x, p=0.9):
    x = np.sort(x); n = len(x); h = (n+1)*p
    if h > n: return x[-1]
    lo = int(np.floor(h)); f = h - lo
    return x[lo-1] + f*(x[lo]-x[lo-1]) if lo < n else x[n-1]

thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
min_nvalid = 10**9
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    for d in range(1, 367):
        if d == 60: continue
        rows = pool_rows(d)
        pool = Bsea[rows]                       # (121, nsea)
        min_nvalid = min(min_nvalid, int(np.isfinite(pool).min()))
        thr[d-1] = hazen_vec(pool)
        clim[d-1] = np.nanmean(pool, axis=0)
print("min pool nvalid over all (d, cell):", min_nvalid)
print("NaN thr:", int(np.isnan(thr).sum()), " NaN clim:", int(np.isnan(clim).sum()))

# independent per-cell verification for a sample of doys
rng = np.random.default_rng(7)
for d in [1, 31, 59, 61, 153, 200, 244, 336, 366]:
    rows = pool_rows(d)
    for c in rng.integers(0, nsea, 6):
        pool = Bsea[rows, c]
        pv = pool[np.isfinite(pool)]
        assert np.isclose(thr[d-1, c], hazen_naive(pv)), (d, c)
        assert np.isclose(clim[d-1, c], pv.mean()), (d, c)
print("independent per-cell verification OK (9 doys x 6 cells)")
np.save('/work/data/thr_raw.npy', thr)
np.save('/work/data/clim_raw.npy', clim)
print("done", round(time.time()-t0, 1), "s")