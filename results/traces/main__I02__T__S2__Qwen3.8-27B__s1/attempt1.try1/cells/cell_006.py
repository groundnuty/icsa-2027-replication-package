import numpy as np
from datetime import date, timedelta

# --- verify hazen quantile implementation ---
def hazen_q(P, p=0.9):
    # P: (n, K) float64, NaN allowed -> returns (n,) quantile ignoring NaN (NaN if none valid)
    n, K = P.shape
    valid = np.isfinite(P)
    cnt = valid.sum(axis=1)
    order = np.argsort(P, axis=1, kind='stable')
    S = np.take_along_axis(P, order, axis=1)
    h = p * cnt - 0.5                      # 0-based position
    j0 = np.floor(h).astype(np.int64)
    frac = h - j0
    j0c = np.clip(j0, 0, K-1)
    j1 = j0 + 1
    v0 = np.take_along_axis(S, j0c[:, None], axis=1).ravel()
    v1 = np.take_along_axis(S, np.clip(j1, 0, K-1)[:, None], axis=1).ravel()
    ok = cnt > 0
    q = np.full(n, np.nan)
    inter = ok & (j1 < cnt)
    q[ok & ~inter] = v0[ok & ~inter]
    q[inter] = v0[inter] + frac[inter] * (v1[inter] - v0[inter])
    return q

rng = np.random.default_rng(0)
for trial in range(200):
    n = rng.integers(1, 200)
    P = rng.normal(size=(n,))
    m = rng.random(n) < 0.3
    Pm = P.copy()
    Pm[m] = np.nan
    mine = hazen_q(Pm[None, :])[0]
    ref = np.nan if Pm[~np.isnan(Pm)].size == 0 else np.quantile(Pm[~np.isnan(Pm)], 0.9, method='hazen')
    assert (np.isnan(mine) and np.isnan(ref)) or abs(mine - ref) < 1e-12*max(1,abs(ref)), (mine, ref, n)
print("hazen quantile implementation verified (200 random trials)")

# --- day-of-year mapping (leap-year calendar, 1..366) ---
doy_md = {}
d = date(2004, 1, 1)
for k in range(366):
    doy_md[k+1] = (d.month, d.day)
    d += timedelta(days=1)
for k in [1, 59, 60, 61, 62, 153, 244, 365, 366]:
    print(k, doy_md[k])
assert doy_md[60] == (2, 29)

# --- pool date indices for each d ---
import pandas as pd
t0 = pd.Timestamp('1991-12-27').to_datetime64()
# load time array from npz
import xarray as xr
z = np.load('work/sst.npz')
tb = z['tb']  # (4028,) datetime64[ns]
tt = z['tt']
date_to_i = {date.fromisoformat(ts.astype('datetime64[D]').astype(str)): i for i, ts in enumerate(tb)}
def date_to_i2(y, m, dd): return date_to_i[date(y, m, dd)]

pool_idx = {}
for d in range(1, 367):
    if d == 60: continue
    m, dd = doy_md[d]
    idxs = []
    seen = set()
    for y in range(1992, 2003):
        b = date(y, m, dd)
        for delta in range(-5, 6):
            dt = b + timedelta(days=delta)
            assert date(1991,12,27) <= dt <= date(2003,1,5), (d, y, delta, dt)
            if dt not in seen:
                seen.add(dt)
                idxs.append(date_to_i2(*dt))
    pool_idx[d] = np.asarray(idxs, dtype=np.int64)
ks = {len(v) for v in pool_idx.values()}
print("pool sizes:", ks, "n d values:", len(pool_idx))
# sanity: d=1 pool includes 1991-12-27 and 2003-01-05?
d1 = pool_idx[1]
print("d=1 first dates:", [tb[i].astype(str) for i in d1[:6]], "last:", [tb[i].astype(str) for i in d1[-6:]])
d366 = pool_idx[366]
print("d=366 last dates:", [tb[i].astype(str) for i in d366[-6:]])
d59 = pool_idx[59]
# leap year 1996-02-28 window should include 1996-02-29
print("d=59 contains 1996-02-29:", tb[date_to_i2(1996,2,29)].astype(str) in [tb[i].astype(str) for i in d59])
np.save('work/pool_idx.npy', np.array(sorted(pool_idx.keys()), dtype=np.int32))
import pickle
with open('work/pool_idx.pkl','wb') as fh: pickle.dump(pool_idx, fh)
print("pools saved")
