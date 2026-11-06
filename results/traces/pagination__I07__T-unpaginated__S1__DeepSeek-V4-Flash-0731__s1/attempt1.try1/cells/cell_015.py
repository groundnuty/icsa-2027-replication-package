
import numpy as np
import pickle
import datetime
import time

# Load saved data
baseline_sst = np.load('/tmp/baseline_sst.npy')
with open('/tmp/date_indices.pkl', 'rb') as f:
    date_indices = pickle.load(f)
with open('/tmp/ext_dates.pkl', 'rb') as f:
    ext_dates_str = pickle.load(f)
sea_cells = np.load('/tmp/sea_cells.npy')

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Sea cells: {sea_cells.sum()}")

# Reconstruct ext_dates as datetime objects
ext_dates = [datetime.datetime.strptime(s, '%Y%m%d').date() for s in ext_dates_str]

def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

# Build doy_to_indices mapping: doy -> list of time indices
base_start = datetime.date(1992, 1, 1)
base_end = datetime.date(2002, 12, 31)

from collections import defaultdict
doy_to_indices = defaultdict(list)

for i, X in enumerate(ext_dates):
    for delta in range(-5, 6):
        Y = X + datetime.timedelta(days=delta)
        if base_start <= Y <= base_end:
            d = doy_from_date(Y)
            if d != 60:
                doy_to_indices[d].append(i)

# Verify all doys have 121 indices
for d in range(1, 367):
    if d != 60:
        assert len(doy_to_indices[d]) == 121, f"doy {d} has {len(doy_to_indices[d])} indices"

print("All doys have 121 indices")

# Now compute thresholds and climatologies
# For each doy, for each sea cell, compute statistics
# We'll store as arrays of shape (366, n_lat, n_lon) where n_lat, n_lon are region dims

n_lat, n_lon = sea_cells.shape
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

# Get sea cell indices
sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])
print(f"Number of sea cells: {n_sea}")

# Compute for each doy
start = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    indices = doy_to_indices[d]
    # Extract data: (121, n_lat, n_lon) for the pool dates
    pool_data = baseline_sst[indices]  # (121, 60, 60)
    # Only use sea cells
    for si in range(n_sea):
        li, loi = sea_idx[0][si], sea_idx[1][si]
        values = pool_data[:, li, loi]
        valid = values[~np.isnan(values)]
        if len(valid) > 0:
            # Threshold: 90th percentile using Hazen method (numpy default method='hazen' is type 5)
            # Actually, let me check numpy's default method for percentile
            # numpy.percentile default is method='linear' which is Hyndman-Fan type 7
            # But the task says method="hazen" which is Hyndman-Fan type 5
            threshold[d, li, loi] = np.percentile(valid, 90, method='hazen')
            climatology[d, li, loi] = np.mean(valid)
        else:
            threshold[d, li, loi] = np.nan
            climatology[d, li, loi] = np.nan

elapsed = time.time() - start
print(f"Computed thresholds and climatologies in {elapsed:.1f}s")

# Set day 60 to mean of days 59 and 61
threshold[60] = (threshold[59] + threshold[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Save intermediate results
np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
print("Saved raw thresholds and climatologies")
