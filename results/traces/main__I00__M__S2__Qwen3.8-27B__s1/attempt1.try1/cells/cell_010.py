import numpy as np, datetime as dt

S = np.load("/tmp/S.npy")
ncells, ndays = S.shape
base = dt.date(1991,12,27)
dates = [base + dt.timedelta(days=k) for k in range(ndays)]
month_days = np.cumsum([0,31,29,31,30,31,30,31,31,30,31,30,31])
doy = np.array([month_days[d.month-1] + d.day for d in dates])

ord0 = (dt.date(1992,1,1) - base).days
ord1 = (dt.date(2002,12,31) - base).days
print("baseline span idx:", ord0, ord1, dates[ord0], dates[ord1])

pools = {d: [] for d in range(1,367)}
for k in range(ord0, ord1+1):
    d = int(doy[k])
    pools[d] += [k+off for off in range(-5,6)]
pool_arr = [np.unique(pools[d]) if d != 60 else np.array([], dtype=int) for d in range(1,367)]
assert pool_arr[59].size == 0
sizes = collections.Counter(len(p) for p in pool_arr if p.size) if False else {}
import collections
sizes = collections.Counter(len(p) for p in pool_arr if len(p))
print("pool sizes:", dict(sizes))

j0 = (dt.date(2004,6,1) - base).days
j1 = (dt.date(2004,8,31) - base).days
print("target slice:", j0, j1, "ndays:", j1-j0+1)
St = S[:, j0:j1+1]
sea = ~np.isnan(St).any(axis=1)
nsea = int(sea.sum())
print("sea cells:", nsea)
Ssea = S[sea]

thr = np.full((366, nsea), np.nan)
clim = np.full((366, nsea), np.nan)
for d in range(1,367):
    if d == 60: continue
    A = Ssea[:, pool_arr[d-1]]
    assert A.shape[0] == 121
    assert not np.isnan(A).any()
    thr[d-1] = np.quantile(A, 0.9, axis=0, method='hazen')
    clim[d-1] = A.mean(axis=0)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("pre-smooth finite:", np.isfinite(thr).all(), np.isfinite(clim).all())

def smooth31(x):
    z = np.concatenate([x, x], axis=0)
    C = np.empty((z.shape[0]+1, x.shape[1]), dtype=np.float64)
    C[0] = 0.0
    np.cumsum(z, axis=0, out=C[1:])
    f = (np.arange(366) - 15) % 366
    return (C[f+31] - C[f]) / 31.0

thr_s = smooth31(thr); clim_s = smooth31(clim)
# verify against explicit window mean for a few cells/days
rng = np.random.default_rng(0)
for _ in range(50):
    c = int(rng.integers(nsea)); d = int(rng.integers(366))
    w = [(d-1+i) % 366 for i in range(-15,16)]
    assert np.isclose(thr_s[d,c], thr[w,c].mean()), (d,c)
    assert np.isclose(clim_s[d,c], clim[w,c].mean())
print("smoothing verified (wraparound), thr_s finite:", np.isfinite(thr_s).all())

np.save("/tmp/thr_s.npy", thr_s); np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/sea.npy", sea); np.save("/tmp/st.npy", St); np.save("/tmp/doy.npy", doy)
print("thr_s range:", thr_s.min(), thr_s.max())
print("sample smoothed thr for doys 153-155, cells 0-4:\n", thr_s[152:155, :5])
