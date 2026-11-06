import numpy as np, time, warnings
doy_ext = np.load('doy_ext.npy').astype(int)
base_ext = np.load('base_ext.npy')  # (4028,60,60) float64

t0 = time.time()
thresh_raw = np.full((366,60,60), np.nan, dtype=np.float64)
clim_raw = np.full((366,60,60), np.nan, dtype=np.float64)
pool_sizes = np.zeros(366, dtype=int)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', category=RuntimeWarning)
    for d in range(1,367):
        if d == 60:
            continue
        idx = np.where(np.abs(doy_ext - d) <= 5)[0]
        pool = base_ext[idx]
        pool_sizes[d-1] = pool.shape[0]
        thresh_raw[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
        clim_raw[d-1] = np.nanmean(pool, axis=0)
t1 = time.time()
print('raw pools done in', round(t1-t0,1), 's')

# day 60 (0-based 59) = mean(day59 (58), day61 (60))
thresh_raw[59] = 0.5*(thresh_raw[58] + thresh_raw[60])
clim_raw[59]   = 0.5*(clim_raw[58]   + clim_raw[60])
print('day60 filled. thresh d59/60/61 (cell 0,0):', thresh_raw[58,0,0], thresh_raw[59,0,0], thresh_raw[60,0,0])
print('clim d59/60/61 (cell 0,0):', clim_raw[58,0,0], clim_raw[59,0,0], clim_raw[60,0,0])
print('pool_sizes[0], [365]:', pool_sizes[0], pool_sizes[365])
# NaN pattern: how many cells have NaN threshold on an interior day
print('NaN thresh cells at day 100:', np.isnan(thresh_raw[99]).sum(), 'of', 60*60)
print('NaN thresh cells at day 366:', np.isnan(thresh_raw[365]).sum())

def smooth31(arr):
    out = np.zeros_like(arr)
    for k in range(-15, 16):
        out += np.roll(arr, k, axis=0)
    return out / 31.0

thresh = smooth31(thresh_raw)
clim = smooth31(clim_raw)
np.save('thresh.npy', thresh); np.save('clim.npy', clim)
np.save('thresh_raw.npy', thresh_raw); np.save('clim_raw.npy', clim_raw)
print('smoothed; thresh[151,0,0] (Jun1):', thresh[151,0,0], 'clim[151,0,0]:', clim[151,0,0])
print('thresh NaNs total:', np.isnan(thresh).sum(), 'clim NaNs total:', np.isnan(clim).sum())
