import numpy as np, datetime as dt, json, warnings, time

t0 = time.time()
Sb = np.load('Sb.npy'); St = np.load('St.npy')
base_dates = np.load('base_dates.npy'); tgt_dates = np.load('tgt_dates.npy')
print('shapes', Sb.shape, St.shape, base_dates[0], base_dates[-1], tgt_dates[0], tgt_dates[-1])

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]  # leap-style cumulative days
def doy_of(d):  # d: datetime.date -> leap-style doy by (month, day) only
    return CUM[d.month-1] + d.day

for s, exp in [('1992-01-01',1),('1992-02-28',59),('1992-02-29',60),('1992-03-01',61),
               ('1993-03-01',61),('1993-12-31',366),('1992-12-31',366),('2009-06-01',153),
               ('2009-08-31',244),('1991-12-27',361),('1991-12-31',366),('2003-01-05',5)]:
    v = doy_of(dt.date.fromisoformat(s))
    assert v == exp, (s, v, exp)
print('DOY mapping OK (leap-style by month/day; non-leap years have no day 60)')

q = np.quantile(np.array([1.,2.,3.,4.]), [0.25,0.5,0.75], method='hazen')
print('hazen check [1,2,3,4] ->', q, '(MATLAB default: 1.75 2.5 3.25)')

k0 = int(np.where(base_dates == np.datetime64('1992-01-01'))[0][0])
k1 = int(np.where(base_dates == np.datetime64('2002-12-31'))[0][0])
print('baseline index range', k0, k1)
doy_base = np.array([doy_of(dt.date.fromisoformat(str(base_dates[k])[:10])) for k in range(k0, k1+1)])

thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
pool_sizes = []
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1, 367):
        if d == 60: continue
        ks = np.where(doy_base == d)[0] + k0
        idx = np.unique((ks[:, None] + np.arange(-5, 6)[None, :]).ravel())
        assert idx.min() >= 0 and idx.max() < Sb.shape[0], (d, idx.min(), idx.max())
        pool = Sb[idx]
        pool_sizes.append(pool.shape[0])
        thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
pool_sizes = np.array(pool_sizes)
print('pool sizes: min %d max %d' % (pool_sizes.min(), pool_sizes.max()),
      '| pool[366]=%d pool[365]=%d pool[1]=%d pool[153]=%d pool[60-ish d59]=%d' %
      (pool_sizes[365], pool_sizes[364], pool_sizes[0], pool_sizes[152], pool_sizes[58]))

thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

def circ31(a):
    pad = np.concatenate([a[-15:], a, a[:15]], axis=0)
    cs = np.cumsum(pad, axis=0)
    return (cs[30:] - cs[:-30]) / 31.0
thr = circ31(thr_raw)
clim = circ31(clim_raw)
print('thr range %.3f..%.3f  clim range %.3f..%.3f' % (np.nanmin(thr), np.nanmax(thr), np.nanmin(clim), np.nanmax(clim)))

sea = np.isfinite(St).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)

doy_t = np.array([doy_of(dt.date.fromisoformat(str(t)[:10])) for t in tgt_dates])
print('target DOYs', doy_t[0], '...', doy_t[-1])
hot = np.empty(St.shape, dtype=bool)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for t in range(St.shape[0]):
        hot[t] = St[t] >= thr[doy_t[t]-1]
hot &= sea[None, :, :]
print('hot cell-days:', int(hot.sum()))

mhw = np.zeros(St.shape, dtype=bool)
n_events_cell = 0; lens = []
for i in range(60):
    for j in range(60):
        h = hot[:, i, j]
        if not h.any(): continue
        idx = np.flatnonzero(h)
        breaks = np.where(np.diff(idx) > 1)[0]
        starts = np.concatenate(([0], breaks+1))
        ends   = np.concatenate((breaks, [idx.size-1]))
        runs = [(int(idx[s]), int(idx[e])) for s, e in zip(starts, ends)]
        mhws = [r for r in runs if r[1]-r[0]+1 >= 5]
        if not mhws: continue
        merged = [mhws[0]]
        for r in mhws[1:]:
            gap = r[0] - merged[-1][1] - 1
            if 1 <= gap <= 2:
                merged[-1] = (merged[-1][0], r[1])
            else:
                merged.append(r)
        n_events_cell += len(merged)
        for s, e in merged:
            lens.append(e-s+1)
            mhw[s:e+1, i, j] = True
lens = np.array(lens)
print('per-cell MHWs:', n_events_cell, ' len min/med/max:', lens.min(), int(np.median(lens)), lens.max())

mhw &= sea[None, :, :]
active = mhw.any(axis=(1, 2))
print('active days:', int(active.sum()), 'of', active.size)
events = []
t = 0
while t < active.size:
    if active[t]:
        s = t
        while t+1 < active.size and active[t+1]: t += 1
        events.append((s, t))
    t += 1
ev = [{'onset': str(tgt_dates[s])[:10], 'end': str(tgt_dates[e])[:10]} for s, e in events]
print('regional events:', json.dumps(ev))

np.savez('analysis.npz', thr=thr, clim=clim, hot=hot, mhw=mhw, sea=sea, active=active,
         doy_t=doy_t, thr_raw=thr_raw, clim_raw=clim_raw)
print('done in %.1fs' % (time.time()-t0))
