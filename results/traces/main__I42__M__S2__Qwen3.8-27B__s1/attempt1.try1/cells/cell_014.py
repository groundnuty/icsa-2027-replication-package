import numpy as np, pickle, time
from collections import defaultdict

base = np.load('/tmp/base.npy')
time_all = np.load('/tmp/time_all.npy')
base_dates = time_all[3647:7675]

LEAP_CUM = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
def doy366(dates):
    dates = np.asarray(dates).astype('datetime64[D]')
    m = (dates.astype('datetime64[M]') - dates.astype('datetime64[Y]')).astype(int) + 1
    d = (dates - dates.astype('datetime64[M]')).astype(int) + 1
    return LEAP_CUM[m - 1] + d

bmin = np.datetime64('1992-01-01'); bmax = np.datetime64('2002-12-31')
pools = defaultdict(list)
for k in range(-5, 6):
    b = base_dates + np.timedelta64(k, 'D')
    msk = (b >= bmin) & (b <= bmax)
    idx = np.where(msk)[0]
    dval = doy366(b[msk])
    for i, dd in zip(idx.tolist(), dval.tolist()):
        pools[dd].append(i)

sizes = {d: len(v) for d, v in pools.items()}
assert all(len(v) == 121 for d, v in pools.items() if d != 60)
assert len(pools[60]) == 33   # discarded per spec
print("pools OK: 365 used pools of 121 dates; day 60 (33) discarded")

NC = 3600
thr = np.full((366, NC), np.nan)
clim = np.full((366, NC), np.nan)
t0 = time.time()
for d in list(range(1, 60)) + list(range(61, 367)):
    pool = base[pools[d]]
    thr[d - 1] = np.nanquantile(pool, 0.9, axis=0, method='hazen').reshape(-1)
    clim[d - 1] = np.nanmean(pool, axis=0).reshape(-1)
print(f"loop done in {time.time()-t0:.1f}s")

thr[59] = (thr[58] + thr[60]) / 2.0
clim[59] = (clim[58] + clim[60]) / 2.0

off = (np.arange(366)[:, None] + np.arange(-15, 16)[None, :]) % 366
thr_s = thr[off].mean(axis=1)
clim_s = clim[off].mean(axis=1)

nan_cells = np.where(np.isnan(thr_s).any(axis=0))[0]
print("cells with any NaN smoothed threshold:", len(nan_cells))
np.save('/tmp/thr_s.npy', thr_s)
np.save('/tmp/clim_s.npy', clim_s)

c = 1798
doy_t = np.arange(153, 245)
print("cell", c, "thr 153..157:", np.round(thr_s[doy_t-1, c][:5], 3))
print("cell", c, "thr 240..244:", np.round(thr_s[doy_t-1, c][-5:], 3))
print("cell", c, "clim 153..157:", np.round(clim_s[doy_t-1, c][:5], 3))
