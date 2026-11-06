import numpy as np, pickle, time as _t
from datetime import date, timedelta

z = np.load('work/sst.npz')
SB = z['SB']           # (4028, 60, 60) float64 extended baseline
ST = z['ST']           # (92, 60, 60) float64 target
tb, tt = z['tb'], z['tt']
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)

n_cells = 60*60
SBf = SB.reshape(4028, n_cells)
STf = ST.reshape(92, n_cells)

sea = np.all(np.isfinite(STf), axis=0)          # (n_cells,)
print("sea cells:", sea.sum(), "of", n_cells)

def hazen_q(P, p=0.9):
    n, K = P.shape
    valid = np.isfinite(P)
    cnt = valid.sum(axis=1)
    order = np.argsort(P, axis=1, kind='stable')
    S = np.take_along_axis(P, order, axis=1)
    h = p * cnt - 0.5
    j0 = np.floor(h).astype(np.int64)
    frac = h - j0
    j1 = j0 + 1
    v0 = np.take_along_axis(S, np.clip(j0, 0, K-1)[:, None], axis=1).ravel()
    v1 = np.take_along_axis(S, np.clip(j1, 0, K-1)[:, None], axis=1).ravel()
    ok = cnt > 0
    q = np.full(n, np.nan)
    inter = ok & (j1 < cnt)
    q[ok & ~inter] = v0[ok & ~inter]
    q[inter] = v0[inter] + frac[inter] * (v1[inter] - v0[inter])
    return q

t0 = _t.time()
thr = np.full((n_cells, 366), np.nan)
clim = np.full((n_cells, 366), np.nan)
cnts = np.zeros((n_cells, 366), dtype=np.int32)
for dd in range(1, 367):
    if dd == 60: continue
    P = SBf[pool_idx[dd]].T.copy()   # (n_cells, 121)
    valid = np.isfinite(P)
    cnt = valid.sum(axis=1)
    cnts[:, dd-1] = cnt
    q = hazen_q(P, 0.9)
    s = np.where(valid, P, 0.0).sum(axis=1)
    m = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    thr[:, dd-1] = q
    clim[:, dd-1] = m
print(f"threshold/climatology: {_t.time()-t0:.1f}s")
print("cells with any empty pool (thr NaN pre-impute):", int(np.isnan(thr[:, [d for d in range(366) if d!=59]]).any(axis=1).sum()))
print("cells with all pools >= 50 values:", int((cnts.min(axis=1) >= 50).sum()))

# day 60 = mean of 59 and 61 (pre-smoothing)
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0

def smooth31(a):
    s = np.zeros(366)
    for k in range(-15, 16):
        s += np.roll(a, k)
    return s / 31.0

thr_s = np.array([smooth31(thr[c]) for c in range(n_cells)])
clim_s = np.array([smooth31(clim[c]) for c in range(n_cells)])
print("smoothed. thr NaN cells after smoothing:", int(np.isnan(thr_s).any(axis=1).sum()))

# sanity check vs a direct per-cell reference for a few cells
rng = np.random.default_rng(1)
tbr = z['tb']
def ref_pool(dd, c):
    vals = [float(SBf[i, c]) for i in pool_idx[dd]]
    vals = [v for v in vals if np.isfinite(v)]
    return vals
for c in [0, 123, 1800, 3599]:
    for dd in [1, 59, 61, 100, 200, 366]:
        vals = ref_pool(dd, c)
        exp_q = np.quantile(vals, 0.9, method='hazen')
        exp_m = float(np.mean(vals))
        assert abs(thr[c, dd-1] - exp_q) < 1e-9, (c, dd, thr[c, dd-1], exp_q)
        assert abs(clim[c, dd-1] - exp_m) < 1e-9, (c, dd)
    # smoothing check at a couple of days
    for dd in [1, 60, 153, 366]:
        idxs = [(dd - 1 + k) % 366 for k in range(-15, 16)]
        exp = float(np.mean(thr[c, idxs]))
        assert abs(thr_s[c, dd-1] - exp) < 1e-9, (c, dd)
        expc = float(np.mean(clim[c, idxs]))
        assert abs(clim_s[c, dd-1] - expc) < 1e-9, (c, dd)
print("reference cross-checks passed (spot cells, days incl. 60 and wrap)")

np.savez_compressed('work/thr.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea, cnts=cnts)
print("thr saved", "thr range:", np.nanmin(thr_s[sea]), np.nanmax(thr_s[sea]))
