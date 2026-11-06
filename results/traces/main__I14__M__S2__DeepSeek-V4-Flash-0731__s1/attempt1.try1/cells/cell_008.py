
import numpy as np
import pandas as pd
import pickle

# Load data
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

times = pd.to_datetime(times_int, unit='D')

with open('/tmp/pools.pkl', 'rb') as f:
    pools = pickle.load(f)

# Compute threshold and climatology for all 366 days and all cells
# thresholds[d-1] = threshold for day d
# climatology[d-1] = climatology for day d

n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]

# Initialize
thresholds = np.full((366, n_lat, n_lon), np.nan)
climatology = np.full((366, n_lat, n_lon), np.nan)

# Compute for each day d != 60
for d in range(1, 367):
    if d == 60:
        continue
    idx = pools[d]
    if len(idx) == 0:
        continue
    data = sst_data[idx, :, :]  # (n_pool, 60, 60)
    # Compute mean ignoring NaN
    climatology[d-1, :, :] = np.nanmean(data, axis=0)
    # Compute 90th percentile ignoring NaN
    thresholds[d-1, :, :] = np.nanquantile(data, 0.9, axis=0, method='hazen')

# Day 60 = mean of days 59 and 61
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

print("Thresholds computed. Shape:", thresholds.shape)
print("Climatology computed. Shape:", climatology.shape)

# Check some values
print("Threshold at doy 153, cell (0,0):", thresholds[152, 0, 0])
print("Climatology at doy 153, cell (0,0):", climatology[152, 0, 0])

# Save
np.save('/tmp/thresholds.npy', thresholds)
np.save('/tmp/climatology.npy', climatology)
print("Saved thresholds and climatology")
