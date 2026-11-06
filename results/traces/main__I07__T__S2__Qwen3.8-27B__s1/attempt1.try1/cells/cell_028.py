
import numpy as np, pandas as pd, time
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw_main = np.load('/tmp/mhw/in_mhw.npy')
in_mhw_indep = np.load('/tmp/mhw/in_mhw_indep.npy')
cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_tgt = cum[np.asarray(td.month)-1] + np.asarray(td.day)
C = Y.shape[1]
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
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

thr = np.full((366, C), np.nan)
for d in range(1, 367):
    if d == 60: continue
    p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
    thr[d-1] = hazen90(X[np.concatenate([np.arange(p0-5, p0+6) for p0 in p])])
thr[59] = 0.5*(thr[58] + thr[60])
print("thr %.1fs" % (time.time()-t0))

def circ_smooth31(a):   # main-run method
    n = a.shape[0]
    idx = (np.arange(n)[:, None] + np.arange(-15, 16)[None, :]) % n
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        v = a[idx][:, :, c0:c0+1200]
        valid = np.isfinite(v)
        s = np.sum(np.where(valid, v, 0.0), axis=1)
        cnt = valid.sum(axis=1)
        out[:, c0:c0+1200] = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    return out

def smooth31(a):        # indep-run method
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        blk = ext[:, c0:c0+1200]
        w = np.lib.stride_tricks.sliding_window_view(blk, 31, axis=0)
        v = np.where(np.isfinite(w), w, 0.0)
        cnt = np.isfinite(w).sum(axis=2)
        out[:, c0:c0+1200] = np.where(cnt > 0, v.sum(axis=2) / np.maximum(cnt, 1), np.nan)
    return out

thrS_A = circ_smooth31(thr)
thrS_B = smooth31(thr)
print("smooth %.1fs" % (time.time()-t0))
eq = (np.isfinite(thrS_A) == np.isfinite(thrS_B)).all() and np.allclose(thrS_A, thrS_B, equal_nan=True)
print("thrS_A == thrS_B:", bool(eq))
if not eq:
    bad = (np.abs(thrS_A - thrS_B) > 1e-12) | ((np.isfinite(thrS_A) != np.isfinite(thrS_B)))
    idx = np.argwhere(bad)
    print("smoothing diffs:", len(idx), idx[:8].tolist())
    # show one example
    d0, c0 = idx[0]
    print("example: d(index)=%d c=%d A=%.6f B=%.6f" % (d0, c0, thrS_A[d0,c0], thrS_B[d0,c0]))

with np.errstate(invalid='ignore'):
    hot_A = (Y >= thrS_A[doy_tgt-1])
    hot_B = (Y >= thrS_B[doy_tgt-1])
sea = np.isfinite(Y).all(axis=0)
print("hot_A == hot_B:", bool((hot_A == hot_B).all()), "sea:", int(sea.sum()))
