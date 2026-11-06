import numpy as np

b = np.load("/tmp/mhw/baseline.npy")          # (4028, nsea)
idx = np.load("/tmp/mhw/idx_by_doy.npy", allow_pickle=True)  # 365 arrays
nsea = b.shape[1]
doys = [d for d in range(1, 367) if d != 60]

thr = np.full((nsea, 366), np.nan)
clim = np.full((nsea, 366), np.nan)
for j, d in enumerate(doys):
    pool = b[idx[j]].T                        # (nsea, 121)
    thr[:, d-1] = np.nanquantile(pool, 0.9, method="hazen", axis=1)
    clim[:, d-1] = np.nanmean(pool, axis=1)

# day 60 (index 59) = mean of days 59 (idx 58) and 61 (idx 60)
thr[:, 59] = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0

assert np.isfinite(thr).all() and np.isfinite(clim).all()

# 31-day centred circular moving mean
def smooth31(x):  # x: (nsea, 366)
    ext = np.concatenate([x[:, -15:], x, x[:, :15]], axis=1)   # (nsea, 396)
    c = np.cumsum(ext, axis=1)
    c = np.concatenate([np.zeros((x.shape[0], 1)), c], axis=1) # (nsea, 397)
    return (c[:, 31:] - c[:, :-31]) / 31.0

thr_s = smooth31(thr)
clim_s = smooth31(clim)

# verify smoothing against naive loop for a few cells
for c in (0, 123, 3001):
    for d in (0, 14, 15, 59, 60, 61, 350, 365):
        lo = (d - 15) % 366; hi = (d + 15) % 366
        if lo <= hi:
            naive = thr[lo:hi+1, c].mean()
        else:
            naive = np.concatenate([thr[lo:, c], thr[:hi+1, c]]).mean()
        assert abs(naive - thr_s[d, c]) < 1e-9, (c, d, naive, thr_s[d, c])
print("smoothing verified")

# spot-check a threshold by hand for cell 0, doy 153 (Jun 1): pool = dates in 11 windows Jun1 Y +-5 for Y=1992..2002
i153 = np.where(np.load("/tmp/mhw/baseline_dates.npy") == np.datetime64(datetime.date(2000,6,1)).astype('int64').item() + 0)[0]
import datetime
d0o = datetime.date(1991,12,27).toordinal()
pool_manual = []
for Y in range(1992, 2003):
    for k in range(-5, 6):
        od = datetime.date(Y, 6, 1).toordinal() + k
        ii = od - d0o
        pool_manual.append(b[ii, 0])
pm = np.sort(np.array(pool_manual))
h = 121 * 0.9 - 0.5   # 0-based HF type5 index
lo_i = int(h); frac = h - lo_i
manual_thr = pm[lo_i] + frac * (pm[lo_i+1] - pm[lo_i])
print("manual thr cell0 doy153:", manual_thr, " computed:", thr[0, 152])
print("manual clim cell0 doy153:", pm.mean(), " computed:", clim[0, 152])

np.save("/tmp/mhw/thr_smooth.npy", thr_s)
np.save("/tmp/mhw/clim_smooth.npy", clim_s)
print("saved; thr range:", thr_s.min(), thr_s.max(), "clim range:", clim_s.min(), clim_s.max())
