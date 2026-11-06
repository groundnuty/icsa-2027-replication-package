
import numpy as np
x = np.load('/tmp/thr_s.npy')
# rebuild unsmoothed x from saved smoothed? no - recompute check against raw pools is heavy.
# Instead verify smooth366 on a synthetic random 2d array and on the raw unsmoothed threshold
# recompute raw thr (fast path: redo pools)
import datetime as dt, time
warnings_ok = None
import warnings; warnings.filterwarnings('ignore')
sst_base = np.load('/tmp/sst_base.npy')
bord = np.load('/tmp/bdates.npy')
def doy_of(ordinal):
    d = dt.date.fromordinal(int(ordinal))
    cum = [31,29,31,30,31,30,31,31,30,31,30,31]
    return sum(cum[:d.month-1]) + d.day
b0 = dt.date(1992,1,1).toordinal(); b1 = dt.date(2002,12,31).toordinal()
rows_of_doy = {d: [] for d in range(1,367)}
for i, o in enumerate(bord):
    lo = max(int(o)-5, b0); hi = min(int(o)+5, b1)
    for b in range(lo, hi+1):
        rows_of_doy[doy_of(b)].append(i)
thr = np.full((367,3600), np.nan)
t0=time.time()
for d in range(1,367):
    if d==60: continue
    pool = sst_base[rows_of_doy[d]]
    thr[d] = np.nanquantile(pool, 0.90, axis=0, method='hazen')
thr[60] = 0.5*(thr[59]+thr[61])
xraw = thr[1:]

def smooth366(a2d):
    y = np.r_[a2d[-15:], a2d, a2d[:15]]
    out = np.empty_like(a2d)
    for i in range(366):
        out[i] = y[i:i+31].mean(axis=0)
    return out
sm = smooth366(xraw)
print("re-smoothed equals saved:", np.allclose(sm, x, equal_nan=True))
ok=True
for d in [1,20,60,153,244,352,366]:
    i=d-1
    idxs = np.array([(i+k)%366 for k in range(-15,16)])
    ref = xraw[idxs].mean(axis=0)
    good = np.all(np.equal(ref, sm[i]) | (np.isfinite(ref) & np.isclose(ref, sm[i])))
    if not good: ok=False; print("MISMATCH", d)
print("smoothing check (NaN-aware):", "ok" if ok else "FAIL")
# finite-only allclose too
print("finite allclose:", np.allclose(ref[np.isfinite(ref)], sm[i][np.isfinite(ref)]) if np.isfinite(ref).any() else "n/a")
np.save('/tmp/thr_raw.npy', thr)
print("done %.1f s" % (time.time()-t0))
