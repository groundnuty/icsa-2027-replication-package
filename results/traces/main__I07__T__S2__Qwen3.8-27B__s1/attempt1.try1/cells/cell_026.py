
import numpy as np, pandas as pd, time
t0 = time.time()
X = np.load('/tmp/mhw/ext.npy'); Y = np.load('/tmp/mhw/tgt.npy')
ed = pd.to_datetime(np.load('/tmp/mhw/ext_dates.npy'), unit='D')
td = pd.to_datetime(np.load('/tmp/mhw/tgt_dates.npy'), unit='D')
in_mhw_main = np.load('/tmp/mhw/in_mhw.npy')
in_mhw_indep = np.load('/tmp/mhw/in_mhw_indep.npy')

cum = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
doy_ext = cum[np.asarray(ed.month)-1] + np.asarray(ed.day)
doy_tgt = cum[np.asarray(td.month)-1] + np.asarray(td.day)
C = X.shape[1]; T = 92

# --- main-run method: pandas quantile
b0, b1 = 5, 4023
thr_p = np.full((366, C), np.nan)
with np.errstate(all='ignore'):
    for d in range(1, 367):
        if d == 60: continue
        p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
        pool = X[np.concatenate([np.arange(p0-5, p0+6) for p0 in p])]
        thr_p[d-1] = pd.DataFrame(pool).quantile(0.9, interpolation='hazen', axis=0).to_numpy()
thr_p[59] = 0.5*(thr_p[58] + thr_p[60])
print("pandas thr %.1fs" % (time.time()-t0))

# --- indep method: hazen90
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
thr_h = np.full((366, C), np.nan)
for d in range(1, 367):
    if d == 60: continue
    bs = np.flatnonzero((ed >= pd.Timestamp('1992-01-01')) & (ed <= pd.Timestamp('2002-12-31')))[doy_ext[b0:b1] == d]
    # simpler: same positions as main
    p = b0 + np.flatnonzero(doy_ext[b0:b1] == d)
    thr_h[d-1] = hazen90(X[np.concatenate([np.arange(p0-5, p0+6) for p0 in p])])
thr_h[59] = 0.5*(thr_h[58] + thr_h[60])
print("hazen90 thr %.1fs" % (time.time()-t0))

# compare pre-smoothing thresholds
both = np.isfinite(thr_p) & np.isfinite(thr_h)
print("pre-smooth thr: finite cells match:", bool((np.isfinite(thr_p) == np.isfinite(thr_h)).all()),
      "max diff:", float(np.nanmax(np.abs(thr_p - thr_h))[both.any(axis=0)] if both.any() else np.nan))
dd = np.abs(thr_p - thr_h)
print("pre-smooth max abs diff (finite both):", float(np.nanmax(dd)))

# --- main-run smoothing
def circ_smooth31(a):
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
thrS_p = circ_smooth31(thr_p)
print("smoothed %.1fs" % (time.time()-t0))

# manual element check of circ_smooth31 vs explicit day list d-15..d+15 (1-based)
def manual_smooth(a, d):
    return float(np.nanmean(a[(np.arange(d-16, d+15)) % 366]))
for (d, cc) in [(1, 3000), (5, 1230), (60, 1230), (152, 500), (244, 2000), (366, 3000)]:
    m = manual_smooth(thr_p[:, cc], d)
    print("main-smooth chk d=%d c=%d: %.6f vs %.6f match=%s" % (d, cc, thrS_p[d-1, cc], m, abs(thrS_p[d-1, cc]-m) < 1e-12))

# --- hot arrays from each thrS
with np.errstate(invalid='ignore'):
    hot_p = (Y >= thrS_p[doy_tgt-1])
sea = np.isfinite(Y).all(axis=0)
print("hot_p days:", int(hot_p.sum()), "sea:", int(sea.sum()))
# what would the indep hot be? recompute indep thrS
def smooth31(a):
    ext = np.concatenate([a[-15:], a, a[:15]], axis=0)
    out = np.empty_like(a)
    for c0 in range(0, C, 1200):
        blk = ext[:, c0:c0+1200]
        w = np.lib.stride_tricks.sliding_window_view(blk, 31, axis=0)
        v = np.where(np.isfinite(w), w, 0.0)
        cnt = np.isfinite(w).sum(axis=2)
        out[:, c0:c0+1200] = np.where(cnt > 0, v.sum(axis=2) / np.maximum(cnt, 1), np.nan)
    return out
thrS_h = smooth31(thr_h)
with np.errstate(invalid='ignore'):
    hot_h = (Y >= thrS_h[doy_tgt-1])
print("hot_p == hot_h:", bool((hot_p == hot_h).all()))
if not (hot_p == hot_h).all():
    d2 = hot_p != hot_h
    print("hot diffs:", int(d2.sum()), "sample:", np.argwhere(d2)[:5].tolist())
