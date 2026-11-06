import numpy as np, datetime

b = np.load("/tmp/mhw/baseline.npy")          # (4028, nsea)
idx = [np.asarray(x, dtype=np.int64) for x in np.load("/tmp/mhw/idx_by_doy.npy", allow_pickle=True)]
nsea = b.shape[1]
doys = [d for d in range(1, 367) if d != 60]

thr = np.full((nsea, 366), np.nan)
clim = np.full((nsea, 366), np.nan)
for j, d in enumerate(doys):
    pool = b[idx[j]].T
    thr[:, d-1] = np.nanquantile(pool, 0.9, method="hazen", axis=1)
    clim[:, d-1] = np.nanmean(pool, axis=1)

thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0
assert np.isfinite(thr).all() and np.isfinite(clim).all()

def smooth31(x):
    ext = np.concatenate([x[:, -15:], x, x[:, :15]], axis=1)
    c = np.cumsum(ext, axis=1)
    c = np.concatenate([np.zeros((x.shape[0], 1)), c], axis=1)
    return (c[:, 31:] - c[:, :-31]) / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)

for c in (0, 123, 3001):
    for d in (0, 14, 15, 59, 60, 61, 350, 365):
        lo = (d - 15) % 366; hi = (d + 15) % 366
        if lo <= hi:
            naive = thr[lo:hi+1, c].mean()
        else:
            naive = np.concatenate([thr[lo:, c], thr[:hi+1, c]]).mean()
        assert abs(naive - thr_s[d, c]) < 1e-9, (c, d, naive, thr_s[d, c])
print("smoothing verified")

# hand-check cell 0, doy 153 (Jun 1)
d0o = datetime.date(1991, 12, 27).toordinal()
pool_manual = []
for Y in range(1992, 2003):
    for k in range(-5, 6):
        ii = datetime.date(Y, 6, 1).toordinal() + k - d0o
        pool_manual.append(b[ii, 0])
pm = np.sort(np.array(pool_manual))
h = 121 * 0.9 - 0.5
lo_i = int(h); frac = h - lo_i
manual_thr = pm[lo_i] + frac * (pm[lo_i + 1] - pm[lo_i])
print("manual thr:", manual_thr, "computed:", thr[0, 152])
print("manual clim:", pm.mean(), "computed:", clim[0, 152])

np.save("/tmp/mhw/thr_smooth.npy", thr_s)
np.save("/tmp/mhw/clim_smooth.npy", clim_s)
print("saved; thr range:", thr_s.min(), thr_s.max(), "| clim range:", clim_s.min(), clim_s.max())
