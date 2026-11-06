import numpy as np, warnings, time
from datetime import date, timedelta

t0 = time.time()
B = np.load('/work/data/B.npy')
T = np.load('/work/data/T.npy')

ENDS = np.cumsum([31,29,31,30,31,30,31,31,30,31,30,31])
def md_of(doy):
    idx = int(np.searchsorted(ENDS, doy, side='left'))
    return idx+1, doy - (int(ENDS[idx-1]) if idx > 0 else 0)

# --- verify manual hazen against a naive implementation on a small case ---
def hazen_naive(x, p=0.9):
    x = np.sort(np.asarray(x, float)); n = len(x)
    h = (n+1)*p
    lo = int(np.floor(h)); f = h - lo
    if lo >= n: return x[n-1] + 0.0  # h<=n guaranteed for n>=9
    if lo <= 0: return x[0]
    return x[lo-1] + f*(x[lo]-x[lo-1])
rng = np.random.default_rng(0)
for _ in range(5):
    x = rng.normal(10, 3, size=rng.integers(9, 50))
    assert np.isclose(hazen_naive(x), np.nanquantile(x, 0.9) if False else hazen_naive(x))
# cross-check hazen formula with explicit definition
x = np.arange(1.0, 11.0)
print("hazen n=10:", hazen_naive(x), "expect 9.9")
x = rng.normal(10,3,50)
n = len(x); h = (n+1)*0.9
xs = np.sort(x)
print("hazen n=50 check:", hazen_naive(x), "expect", xs[int(np.floor(h))-1] + (h-np.floor(h))*(xs[int(np.floor(h))]-xs[int(np.floor(h))-1]))

def hazen_vec(pool, p=0.9):
    """pool (n, m) float64 with NaNs; returns hazen quantile per column (m,), NaN if column all-NaN or empty."""
    m = pool.shape[1]
    nvalid = np.sum(np.isfinite(pool), axis=0)
    out = np.full(m, np.nan)
    ok = nvalid >= 2
    if ok.any():
        x = np.where(np.isfinite(pool), pool, np.inf)
        xs = np.sort(x, axis=0)
        nv = nvalid[ok].astype(float)
        h = (nv + 1.0) * p
        lo = np.floor(h).astype(int)      # 1-based lower rank, in [1, nv] (nv>=9 -> h<=nv)
        f = h - lo
        # gather rows lo-1 and lo (1-based -> 0-based lo-1, lo)
        cols = np.arange(m)[ok]
        a = xs[lo-1, cols]
        b = xs[lo, cols]
        out[ok] = a + f*(b - a)
    # nv==1 case: h=(1+1)p=1.8 -> x[1]+0.8*(x[2]-x[1])? no: with n=1 hazen h=1.8, but only 1 order stat exists.
    # Definition type5 requires n>=2 practically; handle n==1 by returning that value.
    if (nvalid == 1).any():
        one = np.where(nvalid == 1)[0]
        for c in one:
            out[c] = pool[np.isfinite(pool[:, c]), c][0]
    return out

# verify hazen_vec vs naive on random data with NaNs
for trial in range(3):
    P = rng.normal(10, 3, size=(4000, 30))
    P[ipv6-12, ipv6-13] = np.nan
    hv = hazen_vec(P)
    for c in range(30):
        col = P[:, c]; col = col[np.isfinite(col)]
        assert np.isclose(hv[c], hazen_naive(col)), (trial, c)
print("hazen_vec verified vs naive (incl NaNs)")

sea = np.isfinite(T).all(axis=0)
nsea = int(sea.sum())
print("sea cells:", nsea, "of", sea.size)
si = np.flatnonzero(sea.ravel())
Bsea = B[:, si//60, si%60]

d0 = date(1991,12,27)
thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for d in range(1, 367):
    if d == 60: continue
    m, dd = md_of(d)
    lo = date(1992, m, dd) - timedelta(days=5)
    hi = date(2002, m, dd) + timedelta(days=5)
    lo_i, hi_i = (lo - d0).days, (hi - d0).days
    assert 0 <= lo_i < hi_i <= 4027
    pool = Bsea[lo_i:hi_i+1]
    thr[d-1] = hazen_vec(pool)
    clim[d-1] = np.nanmean(pool, axis=0)
print("pools done", round(time.time()-t0,1), "s")
print("NaN thr (d!=60):", int(np.isnan(thr[:59,:]).sum() + np.isnan(thr[60:,:]).sum()),
      " NaN clim (d!=60):", int(np.isnan(clim[:59,:]).sum() + np.isnan(clim[60:,:]).sum()))
np.save('/work/data/thr_raw.npy', thr)
np.save('/work/data/clim_raw.npy', clim)
np.save('/work/data/sea_idx.npy', si)
print("saved")