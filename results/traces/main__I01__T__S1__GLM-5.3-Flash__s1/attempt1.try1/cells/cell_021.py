import numpy as np, datetime as dt, json, collections

z1 = np.load('/work/cache_stage1.npz')
z2 = np.load('/work/cache_stage2.npz')
tgt_flat = z1['tgt_sst'].reshape(92, -1)
thr_s, clim_s, tdoys, sea = z2['thr_s'], z2['clim_s'], z2['tdoys'], z2['sea']
nd_t, ncell = tgt_flat.shape

def find_runs(mask):
    m = np.concatenate(([False], mask, [False])).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))

thr_t = thr_s[tdoys - 1, :]
hot = tgt_flat >= thr_t
mhw_span = np.zeros((nd_t, ncell), dtype=bool)
n_pre = n_post = 0
gaps = []
for c in range(ncell):
    if not sea[c]:
        continue
    rs = [(s, e) for (s, e) in find_runs(hot[:, c]) if (e - s) >= 5]
    n_pre += len(rs)
    for (s1, e1), (s2, e2) in zip(rs[:-1], rs[1:]):
        gaps.append(s2 - e1)
    merged = []
    for (s, e) in rs:
        if merged and (s - merged[-1][1]) <= 2:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    n_post += len(merged)
    for (s, e) in merged:
        mhw_span[s:e, c] = True

print('per-cell MHWs: before joining %d, after %d' % (n_pre, n_post))
gaps = np.array(gaps, dtype=int) if gaps else np.array([], dtype=int)
print('gaps between consecutive >=5d hot runs: n=%d min=%s max=%s' % (
    len(gaps), gaps.min() if len(gaps) else None, gaps.max() if len(gaps) else None))
print('gap histogram:', dict(sorted(collections.Counter(gaps.tolist()).items())) if len(gaps) else {})

active = mhw_span.any(axis=1)
print('active days: %d' % int(active.sum()))
ev_runs = find_runs(active)
d0 = dt.date(2008, 6, 1)
events = [{'onset': (d0 + dt.timedelta(days=int(s))).isoformat(),
           'end': (d0 + dt.timedelta(days=int(e - 1))).isoformat()} for (s, e) in ev_runs]
print('regional events:', events)

# diagnostics table
clim_t = clim_s[tdoys - 1, :]
rm_sst = np.nanmean(tgt_flat, axis=1)
rm_clim = np.nanmean(np.where(sea[None, :], clim_t, np.nan), axis=1)
rm_thr = np.nanmean(np.where(sea[None, :], thr_t, np.nan), axis=1)
rm_anom = rm_sst - rm_clim
nhot = hot.sum(axis=1); nmhw = mhw_span.sum(axis=1)
dates = [d0 + dt.timedelta(days=i) for i in range(92)]
print('\n day        SST   clim   thr  anom  #hot #mhw')
for i in list(range(0, 30, 2)) + list(range(84, 92)):
    print(' %s %6.2f %6.2f %6.2f %+5.2f %4d %4d' % (dates[i], rm_sst[i], rm_clim[i], rm_thr[i], rm_anom[i], nhot[i], nmhw[i]))
print('regional-mean anomaly range: %.2f .. %.2f K' % (rm_anom.min(), rm_anom.max()))
np.savez('/work/cache_stage3.npz', mhw_span=mhw_span, active=active, hot=hot)
json.dump(events, open('/work/events.json', 'w'))
print('stage3 saved')
