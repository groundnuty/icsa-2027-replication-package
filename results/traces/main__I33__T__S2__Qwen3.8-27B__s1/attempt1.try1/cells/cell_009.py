import numpy as np, time
t0=time.time()
base = np.load('/tmp/sst_base.npy')           # (4028, 60, 60)
bdates = np.load('/tmp/bdates.npy')           # datetime64[D]
B = bdates.astype('int64')
# day of year from month/day (calendar based)
bd = np.array([int(d.astype('datetime64[D]').astype(object).strftime('%m')) + 0 for d in bdates])  # months
bm = np.array([int(np.datetime_as_string(d, unit='M').split('-')[1]) for d in bdates])
bdom = np.array([int(np.datetime_as_string(d, unit='D')[8:10]) for d in bdates])
import calendar
base_oy = np.array([int(np.datetime_as_string(d, unit='Y')[:4]) for d in bdates])
doy = np.array([np.busday_count if False else 0 for _ in bdates])  # placeholder
# proper doy: ordinal - ordinal(jan1 of same year) + 1
jan1 = np.array([np.datetime64(f'{y}-01-01') for y in base_oy])
doy = (bdates.astype('int64') - jan1.astype('int64')) + 1
print('doy check: first/last', doy[0], doy[-1], 'unique sorted', np.unique(doy)[:5], np.unique(doy)[-5:], 'max', doy.max())
np.save('/tmp/base_doy.npy', doy)

# baseline date indices (1992-01-01 .. 2002-12-31)
bstart = int(np.searchsorted(B, np.datetime64('1992-01-01').astype('int64')))
bend   = int(np.searchsorted(B, np.datetime64('2002-12-31').astype('int64')))
print('baseline range idx', bstart, bend, 'n', bend-bstart+1)
is_baseline = np.zeros(len(B), bool); is_baseline[bstart:bend+1]=True

N, nlat, nlon = base.shape
ncell = nlat*nlon
base2 = base.reshape(N, ncell)
pools = {}
for d in range(1, 367):
    pos = np.nonzero(is_baseline & (doy==d))[0]
    if pos.size == 0:
        pools[d] = np.array([], int); continue
    lo = np.clip(pos[:,None]-5, 0, N-1); hi = np.clip(pos[:,None]+5, 0, N-1)
    idx = np.unique(np.concatenate([np.arange(l, h+1) for l,h in zip(lo,hi)]))
    pools[d] = idx
    if d in (1,2,5,60,61,65,361,365,366):
        print(f'd={d}: n_pool={idx.size}, first date {bdates[idx[0]]}, last date {bdates[idx[-1]]}')
np.save('/tmp/pools.npy', np.array([pools[d] for d in range(1,367)], dtype=object), allow_pickle=True)
sizes = np.array([pools[d].size for d in range(1,367)])
print('pool sizes: min', sizes.min(), 'max', sizes.max(), 'd60 size', pools[60].size)
print('elapsed %.1fs' % (time.time()-t0))
