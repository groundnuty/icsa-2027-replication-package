
import numpy as np
import pandas as pd
import pickle

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

with open('/tmp/pool_indices.pkl', 'rb') as f:
    pool_indices_by_doy = pickle.load(f)

# Check if sea cells have NaN in baseline pools
sea_indices = np.argwhere(sea_mask)
n_sea = len(sea_indices)

# Check a few pools
for doy in [1, 59, 61, 100, 152, 153, 243, 244, 366]:
    if doy == 60:
        continue
    pool_idx = pool_indices_by_doy[doy]
    pool_data = baseline_data[pool_idx]  # (n_pool, n_lat, n_lon)
    
    # Check sea cells
    nan_count = 0
    for lat_i, lon_i in sea_indices[:100]:
        if np.isnan(pool_data[:, lat_i, lon_i]).any():
            nan_count += 1
    print(f"DOY {doy}: pool size={len(pool_idx)}, sea cells with NaN in pool: {nan_count} out of 100 checked")
