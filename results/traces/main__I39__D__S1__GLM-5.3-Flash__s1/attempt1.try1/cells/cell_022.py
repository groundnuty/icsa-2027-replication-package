import numpy as np, time, datetime as dt

coords = np.load('/work/coords.npz', allow_pickle=True)
time_tgt = coords['time_tgt']
tgt64 = np.load('/work/sst_tgt.npy').astype(np.float64)
thr = np.load('/work/thr.npy'); clim = np.load('/work/clim.npy')
sea = np.all(np.isfinite(tgt64), axis=0)

cum = np.array([0,31,60,91,121,152,182,213,244,274,305,335])
doy_t = np.array([cum[t.astype(dt.date).month-1] + t.astype(dt.date).day for t in time_tgt])
print('target dates:', time_tgt[0], '..', time_tgt[-1], '| doys:', doy_t[0], '..', doy_t[-1], '| n unique', len(np.unique(doy_t)))

hot = tgt64 >= thr[doy_t - 1]
print('hot days total:', int(hot.sum()))
any_nan = ~np.isfinite(tgt64).all(axis=0)
all_nan = ~np.isfinite(tgt64).any(axis=0)
print('partial-NaN cells:', int((any_nan & ~all_nan).sum()), '| all-NaN cells:', int(all_nan.sum()))

def mhw_intervals(hot1d):
    n = len(hot1d); ivs = []; j = 0
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
mhw = np.zeros(tgt64.shape, dtype=np.uint8)
n_mhw_total = 0
for i in range(60):
    for k in range(60):
        for s, e in mhw_intervals(hot[:, i, k]):
            mhw[s:e+1, i, k] = 1
            n_mhw_total += 1
print('per-cell loop done %.2fs' % (time.time()-t0))
print('total per-cell MHWs (post-join):', n_mhw_total)
print('mhw mask sum:', int(mhw.sum()))
np.save('/work/mhw.npy', mhw); np.save('/work/sea.npy', sea); np.save('/work/hot.npy', hot)
print('saved.')
