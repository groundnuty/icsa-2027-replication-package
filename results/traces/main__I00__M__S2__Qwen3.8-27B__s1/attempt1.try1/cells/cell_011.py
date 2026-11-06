import numpy as np, datetime as dt

S = np.load("/tmp/S.npy")
ncells, ndays = S.shape
base = dt.date(1991,12,27)
dates = [base + dt.timedelta(days=k) for k in range(ndays)]
month_days = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
doy = np.array([month_days[d.month-1] + d.day for d in dates])
ord0 = (dt.date(1992,1,1) - base).days
ord1 = (dt.date(2002,12,31) - base).days

pools = {d: [] for d in range(1,367)}
for k in range(ord0, ord1+1):
    d = int(doy[k])
    pools[d] += [k+off for off in range(-5,6)]
pool_arr = [np.unique(pools[d]) if d != 60 else np.array([], dtype=int) for d in range(1,367)]

j0 = (dt.date(2004,6,1) - base).days
j1 = (dt.date(2004,8,31) - base).days
St = S[:, j0:j1+1]
sea = ~np.isnan(St).any(axis=1)
nsea = int(sea.sum())
Ssea = S[sea]

bad_shape = []; bad_nan = []
for d in range(1,367):
    if d == 60: continue
    p = pool_arr[d-1]
    A = Ssea[:, p]
    if A.shape[0] != 121: bad_shape.append((d, A.shape, len(p), p.min(), p.max()))
    if np.isnan(A).any():
        n_nan = int(np.isnan(A).sum())
        bad_nan.append((d, n_nan, int(np.isnan(Ssea[:, p]).any(axis=0).sum())))
print("bad shapes:", bad_shape[:10])
print("bad nan:", bad_nan[:10])
