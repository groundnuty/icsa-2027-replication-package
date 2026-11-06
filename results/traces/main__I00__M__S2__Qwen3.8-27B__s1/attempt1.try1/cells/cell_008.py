import numpy as np, datetime as dt, collections

S = np.load("/tmp/S.npy")
ncells, ndays = S.shape
doy = np.load("/tmp/doy.npy")

base = dt.date(1991,12,27)
dates = [base + dt.timedelta(days=k) for k in range(ndays)]
ord0 = 5   # 1992-01-01
ord1 = 4022 # 2002-12-31

pools = {d: [] for d in range(1,367)}
for k in range(ord0, ord1+1):
    d = int(doy[k])
    for off in range(-5,6):
        pools[d].append(k+off)
pool_arr = []
for d in range(1,367):
    pool_arr.append(np.unique(pools[d]) if d != 60 else np.array([], dtype=int))
assert pool_arr[59].size == 0  # d=60 (index 59)
print("pool 60 empty:", pool_arr[59].size == 0, " pool 1 size:", pool_arr[0].size)

# sea cells
toff = 8187 - 3647  # j0 - i0 ; recompute properly
# recompute: i0 = idx of 1991-12-27 = 0 in this array; target starts 2004-06-01
j0 = (dt.date(2004,6,1) - base).days
j1 = (dt.date(2004,8,31) - base).days
print("target slice:", j0, j1, j1-j0+1)
St = S[:, j0:j1+1]
sea = ~np.isnan(St).any(axis=1)
print("sea cells:", int(sea.sum()))
Ssea = S[sea]  # (3301, 4632)

thr = np.full((366, len(sea)), np.nan)
clim = np.full((366, len(sea)), np.nan)
for d in range(1,367):
    if d == 60: continue
    idx = pool_arr[d-1]
    A = Ssea[:, idx]  # (m, 3301)
    assert not np.isnan(A).any(), f"NaN in pool for d={d}"
    thr[d-1] = np.quantile(A, 0.9, axis=0, method='hazen')
    clim[d-1] = A.mean(axis=0)
thr[59] = 0.5*(thr[58] + thr[60])
clim[59] = 0.5*(clim[58] + clim[60])
print("thr finite all:", np.isfinite(thr).all(), " clim finite all:", np.isfinite(clim).all())

# 31-day centred moving mean, wrap around (366 element arrays)
def smooth31(x):  # x: (366, m)
    z = np.concatenate([x, x], axis=0)
    C = np.empty((z.shape[0]+1, x.shape[1]), dtype=np.float64)
    C[0] = 0.0
    np.cumsum(z, axis=0, out=C[1:])
    f = (np.arange(366) - 15) % 366
    return (C[f+31] - C[f]) / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)
print("smoothed thr finite:", np.isfinite(thr_s).all())

# check smoothing against explicit loop for one cell
x = thr[:, 0]
d = 7  # e.g. day 8
w = [(d-1+i) % 366 for i in range(-15,16)]
assert np.isclose(thr_s[d,0], x[w].mean()), (thr_s[d,0], x[w].mean())
d = 0
w = [(d-1+i) % 366 for i in range(-15,16)]
assert np.isclose(thr_s[d,0], x[w].mean())
d = 14
w = [(d-1+i) % 366 for i in range(-15,16)]
assert np.isclose(thr_s[d,0], x[w].mean())
print("smoothing verified incl. wraparound")

np.save("/tmp/thr_s.npy", thr_s)
np.save("/tmp/clim_s.npy", clim_s)
np.save("/tmp/sea.npy", sea)
np.save("/tmp/st.npy", St)
print("thr range:", thr_s.min(), thr_s.max(), " clim range:", clim_s.min(), clim_s.max())
print("sample thr doy153..155 (first 5 sea cells):", thr_s[152:155, :5])
