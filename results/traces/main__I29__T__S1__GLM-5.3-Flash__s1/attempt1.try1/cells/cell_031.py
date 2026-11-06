import numpy as np, time
doy_ext = np.load('doy_ext.npy').astype(int)
base_ext = np.load('base_ext.npy')  # (4028,60,60) float64

t0 = time.time()
thresh_raw = np.empty((366,60,60), dtype=np.float64)
clim_raw = np.empty((366,60,60), dtype=np.float64)
pool_sizes = np.empty(366, dtype=int)
for d in range(1,367):
    if d == 60:
        continue
    idx = np.where(np.abs(doy_ext - d) <= 5)[0]
    pool = base_ext[idx]                       # (n,60,60)
    pool_sizes[d] = pool.shape[0]
    thresh_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    clim_raw[d-1] = np.nanmean(pool, axis=0)
t1 = time.time()
print('raw pools done in', round(t1-t0,1), 's')

# day 60 = mean(day59, day61) (0-based idx 58 and 60)
thresh_raw[59] = 0.5*(thresh_raw[58] + thresh_raw[60])
clim_raw[59]   = 0.5*(clim_raw[58]   + clim_raw[60])
pool_sizes[59] = 0
print('day60 filled. thresh day59/60/61 mean (cell 0,0):', thresh_raw[58,0,0], thresh_raw[59,0,0], thresh_raw[60,0,0])
print('clim day59/60/61 mean (cell 0,0):', clim_raw[58,0,0], clim_raw[59,0,0], clim_raw[60,0,0])

# smooth: unweighted centred 31-day moving mean, wrap mod 366
def smooth31(arr):
    out = np.zeros_like(arr)
    for k in range(-15, 16):
        out += np.roll(arr, k, axis=0)
    return out / 31.0

thresh = smooth31(thresh_raw)
clim = smooth31(clim_raw)
np.save('thresh.npy', thresh); np.save('clim.npy', clim)
np.save('thresh_raw.npy', thresh_raw); np.save('clim_raw.npy', clim_raw)
t2 = time.time()
print('smoothed in', round(t2-t1,1), 's')
print('thresh[151,0,0] (Jun1):', thresh[151,0,0], 'clim[151,0,0]:', clim[151,0,0])
print('threshold NaNs:', np.isnan(thresh).sum(), 'clim NaNs:', np.isnan(clim).sum())
