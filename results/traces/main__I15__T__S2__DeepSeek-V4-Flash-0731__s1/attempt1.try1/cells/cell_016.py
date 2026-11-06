
import numpy as np
import pickle

sst_base = np.load('sst_base.npy')
with open('pools.pkl', 'rb') as f:
    pools = pickle.load(f)

n_lat, n_lon = sst_base.shape[1], sst_base.shape[2]

# Compute thresholds and climatology for all cells
threshold = np.full((367, n_lat, n_lon), np.nan)
climatology = np.full((367, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pools[doy]
    if not idx:
        continue
    data = sst_base[idx, :, :].astype(np.float64)
    for i in range(n_lat):
        for j in range(n_lon):
            vals = data[:, i, j]
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                threshold[doy, i, j] = np.percentile(vals[valid], 90, method='hazen')
                climatology[doy, i, j] = np.mean(vals[valid])

print('Done computing thresholds. Checking NaN...')
# Check which cells have NaN for all DOYs
all_nan = np.all(np.isnan(threshold[1:367]), axis=0)
print('Cells with all-NaN threshold:', all_nan.sum(), 'out of', n_lat*n_lon)
