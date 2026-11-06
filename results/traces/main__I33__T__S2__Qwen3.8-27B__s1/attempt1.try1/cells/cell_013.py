import numpy as np, time
t0=time.time()
tgt = np.load('/tmp/sst_target.npy')        # (92, 60, 60)
tdates = np.load('/tmp/tdates.npy')
thr_s = np.load('/tmp/thr_s.npy')           # (366, 3600)
N, nlat, nlon = tgt.shape
ncell = nlat*nlon
tgt2 = tgt.reshape(N, ncell)

# target day-of-year by (month, day), leap-year calendar
ml = np.array([31,29,31,30,31,30,31,31,30,31,30,31]); pref = np.concatenate([[0], np.cumsum(ml)])
tm = np.array([int(np.datetime_as_string(d, unit='M').split('-')[1]) for d in tdates])
td = np.array([int(np.datetime_as_string(d, unit='D')[8:10]) for d in tdates])
tdoy = pref[tm-1] + td
print('target doy range:', tdoy.min(), tdoy.max(), 'days:', N)

sea = np.isfinite(tgt2).all(axis=0)
print('sea cells:', int(sea.sum()))
thr_sea_finite = np.isfinite(thr_s).all(axis=0)
print('sea == finite-thr set:', bool((sea == thr_sea_finite).all()))

thr_t = thr_s[tdoy-1]          # (92, 3600)
hot = np.zeros((N, ncell), bool)
hot[:, sea] = (tgt2[:, sea] >= thr_t[:, sea])
print('hot fraction among sea:', hot[:, sea].mean())

# per-cell MHW: runs >=5 hot days; join if gap <=2
mask = np.zeros((N, ncell), dtype=np.uint8)
n_mhw = 0
for c in np.nonzero(sea)[0]:
    h = hot[:, c]
    d = np.diff(np.concatenate(([0], h.view(np.int8), [0])))
    starts = np.nonzero(d==1)[0]; ends = np.nonzero(d==-1)[0] - 1
    cand = [(s,e) for s,e in zip(starts,ends) if (e-s+1) >= 5]
    merged = []
    for s,e in cand:
        if merged and s - merged[-1][1] - 1 <= 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s,e))
    n_mhw += len(merged)
    for s,e in merged:
        mask[s:e+1, c] = 1
print('total per-cell MHWs:', n_mhw)

mask3 = np.zeros((N, nlat, nlon), dtype=np.uint8)
li = np.load('/tmp/lat.npy'); lj = np.load('/tmp/lon.npy')
IL, JL = np.meshgrid(np.nonzero(np.isfinite(li))[0], np.nonzero(np.isfinite(lj))[0], indexing='ij')
# careful: rebuild from saved idx
import json
print('elapsed %.1fs' % (time.time()-t0))
np.save('/tmp/mask_flat.npy', mask)
np.save('/tmp/tdoy.npy', tdoy)
np.save('/tmp/sea.npy', sea)
active = mask.any(axis=1)
print('active days:', int(active.sum()), 'of', N)
# regional events
d = np.diff(np.concatenate(([0], active.view(np.int8), [0])))
es = np.nonzero(d==1)[0]; ee = np.nonzero(d==-1)[0]-1
events = [(str(tdates[s]), str(tdates[e])) for s,e in zip(es,ee)]
print('events:', events)
