
import numpy as np
import pickle

# Load data and pools
sst_base = np.load('sst_base.npy')
with open('pools.pkl', 'rb') as f:
    pools = pickle.load(f)

print('sst_base shape:', sst_base.shape)
print('NaN check:', np.isnan(sst_base).sum(), 'out of', sst_base.size)

# For each DOY, compute threshold (90th percentile, Hazen method) and climatology (mean) per cell
# Threshold: 366 x lat x lon
n_lat, n_lon = sst_base.shape[1], sst_base.shape[2]
threshold = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pools[doy]
    if not idx:
        continue
    # Extract data: (n_pool_dates, n_lat, n_lon)
    data = sst_base[idx, :, :].astype(np.float64)
    # For each cell, compute 90th percentile (Hazen) ignoring NaN
    for i in range(n_lat):
        for j in range(n_lon):
            vals = data[:, i, j]
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                threshold[doy, i, j] = np.percentile(vals[valid], 90, method='hazen')
                climatology[doy, i, j] = np.mean(vals[valid])
