import numpy as np
from datetime import datetime, timedelta
import pickle

# Load data
base_sst = np.load('/tmp/base_sst.npy')  # (4028, 60, 60)
sea_mask = np.load('/tmp/sea_mask.npy')  # (60, 60)

# Load the pool dates
with open('/tmp/doy_pool_dates.pkl', 'rb') as f:
    doy_to_pool_dates = pickle.load(f)

# Load base dates
base_dates_str = np.load('/tmp/base_dates.npy')
base_dates = [datetime.strptime(s, '%Y%m%d') for s in base_dates_str]

# Create a mapping from date string to index in base_sst
date_to_idx = {d.strftime('%Y%m%d'): i for i, d in enumerate(base_dates)}

print(f"Number of DOYs: {len(doy_to_pool_dates)}")
print(f"Sea cells: {sea_mask.sum()}")
print(f"Baseline SST shape: {base_sst.shape}")

# Extract indices of sea cells
sea_indices = np.argwhere(sea_mask)
print(f"Sea cell indices: {sea_indices.shape}")

# For each sea cell, extract the baseline SST series
# base_sst is (n_base, 60, 60)
# For each sea cell (lat_i, lon_j), get the SST time series
# We'll extract all sea cell data as a (n_base, n_sea) array
n_sea = sea_mask.sum()
base_sst_sea = base_sst[:, sea_indices[:, 0], sea_indices[:, 1]].T  # (n_sea, n_base)
print(f"Base SST for sea cells: {base_sst_sea.shape}")
np.save('/tmp/base_sst_sea.npy', base_sst_sea)
np.save('/tmp/sea_indices.npy', sea_indices)
