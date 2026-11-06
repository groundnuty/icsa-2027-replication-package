import numpy as np, datetime as dt, json, warnings, time

t0 = time.time()
Sb = np.load('Sb.npy'); St = np.load('St.npy')
base_dates = np.load('base_dates.npy'); tgt_dates = np.load('tgt_dates.npy')

CUM = [0,31,60,91,121,152,182,213,244,274,305,335]
def doy_of(d): return CUM[d.month-1] + d.day

k0 = int(np.where(base_dates == np.datetime64('1992-01-01'))[0][0])
k1 = int(np.where(base_dates == np.datetime64('2002-12-31'))[0][0])
doy_base = np.array([doy_of(dt.date.fromisoformat(str(base_dates[k])[:10])) for k in range(k0, k1+1)])

thr_raw = np.full((366, 60, 60), np.nan)
clim_raw = np.full((366, 60, 60), np.nan)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for d in range(1, 367):
        if d == 60: continue
        ks = np.where(doy_base == d)[0] + k0
        idx = np.unique((ks[:, None] + np.arange(-5, 6)[None, :]).ravel())
        pool = Sb[idx]
        thr_raw[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
thr_raw[59] = 0.5*(thr_raw[58] + thr_raw[60])
clim_raw[59] = 0.5*(clim_raw[58] + clim_raw[60])

# circular centred 31-day moving mean via explicit rolls (offsets d-15..d+15 mod 366)
def circ31(a):
    acc = np.zeros_like(a)
    for k in range(-15, 16):
        acc += np.roll(a, k, axis=0)
    return acc / 31.0
thr = circ31(thr_raw)
clim = circ31(clim_raw)

# brute-force verification of circ31 for a few random (doy, cell) pairs
rng = np.random.default_rng(1)
c = (30, 30)
for dd in [1, 60, 153, 200, 244, 366, 352, 16]:
    wins = [thr_raw[(dd + off - 1) % 366, c[0], c[1]] for off in range(-15, 16)]
    bf = np.mean(wins)
    print('doy %3d cell(30,30): circ31 %10.6f  brute %10.6f  match=%s' %
          (dd, thr[dd-1, c[0], c[1]], bf, np.isclose(thr[dd-1, c[0], c[1]], bf)))
print('thr range %.3f..%.3f  clim range %.3f..%.3f  nan thr=%d nan clim=%d' %
      (np.nanmin(thr), np.nanmax(thr), np.nanmin(clim), np.nanmax(clim), np.isnan(thr).sum(), np.isnan(clim).sum()))

sea = np.isfinite(St).all(axis=0)
print('sea cells:', int(sea.sum()), 'of', sea.size)

doy_t = np.array([doy_of(dt.date.fromisoformat(str(t)[:10])) for t in tgt_dates])
hot = np.empty(St.shape, dtype=bool)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    for t in range(St.shape[0]):
        hot[t] = St[t] >= thr[doy_t[t]-1]
hot &= sea[None, :, :]
print('hot cell-days:', int(hot.sum()), '(fraction of sea cell-days: %.3f)' % (hot.sum()/ (3308*92)))

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
# daily active-cell counts around event boundaries
for s, e in events:
    lo, hi = max(0, s-3), min(active.size, e+4)
    print('  counts t%d..t%d:' % (lo, hi-1), [int(mhw[k].sum()) for k in range(lo, hi)])

np.savez('analysis.npz', thr=thr, clim=clim, hot=hot, mhw=mhw, sea=sea, active=active,
         doy_t=doy_t, thr_raw=thr_raw, clim_raw=clim_raw)
print('done in %.1fs' % (time.time()-t0))
