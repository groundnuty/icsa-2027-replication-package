import numpy as np, time
t0=time.time()
base = np.load('/tmp/sst_base.npy')
bdates = np.load('/tmp/bdates.npy')
doy = np.load('/tmp/base_doy.npy')
B = bdates.astype('int64')
bstart = 5; bend = 4022
is_baseline = np.zeros(len(B), bool); is_baseline[bstart:bend+1]=True

N, nlat, nlon = base.shape
ncell = nlat*nlon
base2 = base.reshape(N, ncell)
pools = {}
for d in range(1, 367):
    pos = np.nonzero(is_baseline & (doy==d))[0]
    if pos.size == 0:
        pools[d] = np.array([], int); continue
    lo = np.clip(pos-5, 0, N-1); hi = np.clip(pos+5, 0, N-1)
    idx = np.unique(np.concatenate([np.arange(l, h+1) for l,h in zip(lo,hi)]))
    pools[d] = idx
    if d in (1,5,59,60,61,65,361,365,366):
        print(f'd={d}: n_pool={idx.size}, dates {bdates[idx[0]]} .. {bdates[idx[-1]]}')
pools_arr = np.array([pools[d] for d in range(1,367)], dtype=object)
np.save('/tmp/pools.npy', pools_arr, allow_pickle=True)
sizes = np.array([pools[d].size for d in range(1,367)])
print('pool sizes: min', sizes.min(), 'max', sizes.max(), 'd60 size', pools[60].size)
# sanity: pool(1) should start 1991-12-27; pool(365) should end 2003-01-05
print('pool1 dates head:', [str(x) for x in bdates[pools[1][:8]]])
print('pool365 dates tail:', [str(x) for x in bdates[pools[365][-8:]]])
print('elapsed %.1fs' % (time.time()-t0))
