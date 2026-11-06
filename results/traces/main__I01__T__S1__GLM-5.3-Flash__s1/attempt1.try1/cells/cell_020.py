import numpy as np, datetime as dt

z1 = np.load('/work/cache_stage1.npz')
z2 = np.load('/work/cache_stage2.npz')
z3 = np.load('/work/cache_stage3.npz')
tgt_flat = z1['tgt_sst'].reshape(92, -1)
thr_s, tdoys, sea = z2['thr_s'], z2['tdoys'], z2['sea']
clim_s = z2['clim_s']
mhw = z3['mhw_span']; hot = z3['hot']
thr_t = thr_s[tdoys-1, :]; clim_t = clim_s[tdoys-1, :]

d0 = dt.date(2008,6,1)
dates = [d0 + dt.timedelta(days=i) for i in range(92)]

anom = tgt_flat - clim_t
rm_anom = np.nanmean(anom, axis=1)
rm_sst = np.nanmean(tgt_flat, axis=1)
rm_thr = np.nanmean(np.where(sea[None,:], thr_t, np.nan), axis=1)
nhot = hot.sum(axis=1)
nmhw = mhw.sum(axis=1)

print(' day        SST   clim   thr   anom   #hot  #mhw')
for i in range(0, 92, 2):
    print(' %s %6.2f %6.2f %6.2f %+5.2f %5d %5d' % (dates[i], rm_sst[i], clim_t[i].mean(), rm_thr[i], rm_anom[i], nhot[i], nmhw[i]))
print('...')
for i in range(80, 92):
    print(' %s %6.2f %6.2f %6.2f %+5.2f %5d %5d' % (dates[i], rm_sst[i], clim_t[i].mean(), rm_thr[i], rm_anom[i], nhot[i], nmhw[i]))
print('anom range: %.2f .. %.2f K' % (rm_anom.min(), rm_anom.max()))
print('days with anom>0: %d; >thr cells any: %d' % (int((rm_anom>0).sum()), int((nhot>0).sum())))

# gap distribution between consecutive >=5-day hot runs per cell
def find_runs(mask):
    m = np.concatenate(([False], mask, [False])).astype(np.int8)
    d = np.diff(m)
    return list(zip(np.flatnonzero(d==1).tolist(), np.flatnonzero(d==-1).tolist()))
gaps = []
for c in np.flatnonzero(sea):
    rs = [(s,e) for (s,e) in find_runs(hot[:,c]) if e-s >= 5]
    for (s1,e1),(s2,e2) in zip(rs[:-1], rs[1:]):
        gaps.append(s2 - e1)
gaps = np.array(gaps) if gaps else np.array([], dtype=int)
print('gaps between consecutive >=5d runs: n=%d, min=%s, max=%s' % (len(gaps), gaps.min() if len(gaps) else None, gaps.max() if len(gaps) else None))
import collections
print('gap histogram:', dict(sorted(collections.Counter(gaps.tolist()).items()) if len(gaps) else {}))
