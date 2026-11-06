import numpy as np, time
t0=time.time()
base = np.load('/tmp/sst_base.npy')
N, nlat, nlon = base.shape
ncell = nlat*nlon
base2 = base.reshape(N, ncell)
pools = np.load('/tmp/pools.npy', allow_pickle=True)  # list of arrays, pools[d-1]

thr = np.full((366, ncell), np.nan)
climo = np.full((366, ncell), np.nan)
nanpool_days = []
for d in range(1, 367):
    idx = pools[d-1]
    if idx.size == 0: continue
    vals = base2[idx]
    thr[d-1] = np.nanquantile(vals, 0.9, method='hazen', axis=0)
    climo[d-1] = np.nanmean(vals, axis=0)
    if d != 60:
        allnan = np.all(~np.isfinite(vals), axis=0)
        if allnan.any(): nanpool_days.append((d, int(allnan.sum())))
print('days with fully-NaN pools for some cells:', nanpool_days)

# day 60 fill
thr[59] = 0.5*(thr[58] + thr[60])
climo[59] = 0.5*(climo[58] + climo[60])

def smooth366(V):
    W = np.concatenate([V, V, V])
    out = np.empty_like(V)
    for i in range(366):
        out[i] = W[i+366-15 : i+366+16].mean(axis=0)
    return out

thr_s = smooth366(thr)
climo_s = smooth366(climo)
np.save('/tmp/thr.npy', thr); np.save('/tmp/climo.npy', climo)
np.save('/tmp/thr_s.npy', thr_s); np.save('/tmp/climo_s.npy', climo_s)

fin_thr = np.isfinite(thr_s)
print('cells with all-finite smoothed thr:', int(fin_thr.all(axis=0).sum()), 'of', ncell)
print('cells with all-finite smoothed climo:', int(np.isfinite(climo_s).all(axis=0).sum()))
# example: a sea cell and a land cell
print('thr_s range (finite):', np.nanmin(thr_s), np.nanmax(thr_s))
print('climo_s range (finite):', np.nanmin(climo_s), np.nanmax(climo_s))
print('elapsed %.1fs' % (time.time()-t0))
