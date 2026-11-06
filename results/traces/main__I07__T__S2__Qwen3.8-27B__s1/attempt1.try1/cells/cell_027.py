
import numpy as np, pandas as pd, time
t0 = time.time()
# recompute both thresholds again (they weren't saved) -- but that's ~10min; instead re-derive from the saved indep mask? 
# Better: recompute only what's needed. We still have thr arrays? No - state lost. Recompute thr_h (fast method) only,
# and compare with a *few* pandas-quantile cells computed on demand.
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
doy_tgt = cum[np.asarray(td.month)-1] + np.asarray(td.day)
C = X.shape[1]
b0, b1 = 5, 4023

def hazen90(pool):
    p = np.where(np.isnan(pool), np.inf, pool)
    p = np.sort(p, axis=0)
    rows = p.shape[0]
    n = (p < np.inf).sum(axis=0)
    n1 = np.where(n == 0, 1, n).astype(np.float64)
    ifl = 0.9 * n1 + 0.5
    lo = np.clip(np.floor(ifl).astype(np.int64), 1, rows)
    frac = (ifl - lo).astype(np.float64)
    x1 = np.take_along_axis(p, (lo-1)[None, :], axis=0)
    x2idx = np.minimum(np.minimum(lo, np.where(n == 0, 1, n - 1)), rows - 1).astype(np.int64)
    x2 = np.take_along_axis(p, x2idx[None, :], axis=0)
    out = x1 + frac * (x2 - x1)
    return np.where(n == 0, np.nan, out)

pos_by_d = {}
for d in range(1, 367):
    if d == 60: continue
    p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
    pos_by_d[d] = np.concatenate([np.arange(p0-5, p0+6) for p0 in p])

# spot comparison: pandas quantile vs hazen90 on a few (d, cell)
import warnings
with np.errstate(all='ignore'), warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in [1, 100, 152, 153, 183, 244, 300, 366]:
        pool = X[pos_by_d[d]]
        qp = pd.DataFrame(pool).quantile(0.9, interpolation='hazen', axis=0).to_numpy()
        qh = hazen90(pool)
        print("d=%d: max abs diff pandas vs hazen90 = %.3e, nan-pattern equal: %s" % (
            d, float(np.nanmax(np.abs(qp - qh))), bool((np.isfinite(qp) == np.isfinite(qh)).all())))
print("spot done %.1fs" % (time.time()-t0))
