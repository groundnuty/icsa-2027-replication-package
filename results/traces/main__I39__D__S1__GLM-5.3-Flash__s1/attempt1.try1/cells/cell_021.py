import numpy as np, time

coords = np.load('/work/coords.npz', allow_pickle=True)
time_tgt = coords['time_tgt']
tgt64 = np.load('/work/sst_tgt.npy').astype(np.float64)   # (92,60,60)
thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
sea = np.all(np.isfinite(tgt64), axis=0)
print('sea cells:', int(sea.sum()))

# doy per target date (by month/day, Feb29 convention)
cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy_t = np.array([cum[m-1] + d for m, d in ((t.astype('datetime64[M]').astype(int)%12+1, int(t.astype('datetime64[D]')%100)) for t in time_tgt)])
# safer explicit computation
import datetime as dt
doy_t2 = np.array([cum[t.astype(dt.date).month-1] + t.astype(dt.date).day for t in time_tgt])
assert np.array_equal(doy_t, doy_t2)
print('target doys:', doy_t[0], '..', doy_t[-1], '| unique count', len(np.unique(doy_t)))

# hot: NaN >= x is False
hot = tgt64 >= thr[doy_t - 1]
print('hot days total:', int(hot.sum()))

# any cells partially NaN in target period (non-sea but not all-NaN)?
any_nan = ~np.isfinite(tgt64).all(axis=0)
all_nan = ~np.isfinite(tgt64).any(axis=0)
partial = any_nan & ~all_nan
print('partial-NaN cells (non-sea, not all-NaN):', int(partial.sum()))

# per-cell MHW intervals with joining
def mhw_intervals(hot1d):
    n = len(hot1d)
    ivs = []
    j = 0
    while j < n:
        if hot1d[j]:
            e = j
            while e+1 < n and hot1d[e+1]: e += 1
            if e - j + 1 >= 5: ivs.append([j, e])
            j = e + 1
        else:
            j += 1
    merged = []
    for s, e in ivs:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return merged

t0 = time.time()
nt = tgt64.shape[0]
mhw = np.zeros(tgt64.shape, dtype=np.uint8)
n_mhw_total = 0
n_mhw_prejoin = 0
for i in range(60):
    for k in range(60):
        ivs = mhw_intervals(hot[:, i, k])
        n_mhw_prejoin += 0
        for s, e in ivs:
            mhw[s:e+1, i, k] = 1
            n_mhw_total += 1
print('per-cell MHW loop done %.2fs' % (time.time()-t0))
print('total per-cell MHWs (post-join):', n_mhw_total)
print('mhw mask sum:', int(mhw.sum()))
np.save('/work/mhw.npy', mhw)
np.save('/work/sea.npy', sea)
np.save('/work/hot.npy', hot)
