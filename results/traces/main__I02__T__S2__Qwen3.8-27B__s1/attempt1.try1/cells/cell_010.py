import numpy as np, pickle, time as _t
from datetime import date, timedelta

z = np.load('work/sst.npz')
SB = z['SB']; ST = z['ST']; tb, tt = z['tb'], z['tt']
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)
n_cells = 3600
SBf = SB.reshape(4028, n_cells)
STf = ST.reshape(92, n_cells)
sea = np.all(np.isfinite(STf), axis=0)
print("sea cells:", sea.sum())

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
cnts = np.full((n_cells, 366), -1, dtype=np.int32)
for dd in range(1, 367):
    if dd == 60: continue
    P = SBf[pool_idx[dd]].T.copy()
    valid = np.isfinite(P)
    cnt = valid.sum(axis=1)
    cnts[:, dd-1] = cnt
    q = hazen_q(P, 0.9)
    s = np.where(valid, P, 0.0).sum(axis=1)
    m = np.where(cnt > 0, s / np.maximum(cnt, 1), np.nan)
    thr[:, dd-1] = q
    clim[:, dd-1] = m
print(f"threshold/climatology: {_t.time()-t0:.1f}s")
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0
def smooth31(a):
    s = np.zeros(366)
    for k in range(-15, 16):
        s += np.roll(a, k)
    return s / 31.0
thr_s = np.array([smooth31(thr[c]) for c in range(n_cells)])
clim_s = np.array([smooth31(clim[c]) for c in range(n_cells)])
print("NaN-threshold cells (after smoothing):", int(np.isnan(thr_s).any(axis=1).sum()))
print("min pool size per cell (d!=60):", cnts[:, [d for d in range(366) if d!=59]].min(axis=1).min())
np.savez_compressed('work/thr.npz', thr=thr, clim=clim, thr_s=thr_s, clim_s=clim_s, sea=sea, cnts=cnts)
print("saved work/thr.npz")
