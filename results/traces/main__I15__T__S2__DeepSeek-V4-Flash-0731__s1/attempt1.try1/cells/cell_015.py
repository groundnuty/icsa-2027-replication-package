
import numpy as np
import pickle

sst_base = np.load('sst_base.npy')
with open('pools.pkl', 'rb') as f:
    pools = pickle.load(f)

n_lat, n_lon = sst_base.shape[1], sst_base.shape[2]
print('Shapes:', sst_base.shape, n_lat, n_lon)

# threshold[doy] where doy is 1-indexed, so array of size 367 (index 0 unused, index 366 = DOY 366)
threshold = np.full((367, n_lat, n_lon), np.nan)
climatology = np.full((367, n_lat, n_lon), np.nan)

# This might be slow. Let me vectorize per DOY instead of per cell.
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pools[doy]
    if not idx:
        continue
    data = sst_base[idx, :, :].astype(np.float64)
    # Compute per cell: 90th percentile and mean, ignoring NaN
    # Vectorized: for each cell
    for i in range(n_lat):
        for j in range(n_lon):
            vals = data[:, i, j]
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                threshold[doy, i, j] = np.percentile(vals[valid], 90, method='hazen')
                climatology[doy, i, j] = np.mean(vals[valid])

print('Threshold non-NaN count:', np.sum(~np.isnan(threshold)))
print('Climatology non-NaN count:', np.sum(~np.isnan(climatology)))
print('Threshold sample:', threshold[150, 30, 30])
print('Clim sample:', climatology[150, 30, 30])
