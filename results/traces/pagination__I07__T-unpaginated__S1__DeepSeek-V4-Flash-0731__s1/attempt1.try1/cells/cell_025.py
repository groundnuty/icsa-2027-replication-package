
import numpy as np
import pickle
import datetime
import time
from collections import defaultdict

# Load baseline data and convert to float64
start = time.time()
baseline_sst = np.load('/tmp/baseline_sst.npy').astype(np.float64)
print(f"Baseline SST loaded and converted to float64: {baseline_sst.shape}, dtype={baseline_sst.dtype}")

# Load date mappings
with open('/tmp/date_indices.pkl', 'rb') as f:
    date_indices = pickle.load(f)
with open('/tmp/ext_dates.pkl', 'rb') as f:
    ext_dates_str = pickle.load(f)

ext_dates = [datetime.datetime.strptime(s, '%Y%m%d').date() for s in ext_dates_str]

def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

# Build doy_to_indices mapping
base_start = datetime.date(1992, 1, 1)
base_end = datetime.date(2002, 12, 31)
doy_to_indices = defaultdict(list)

for i, X in enumerate(ext_dates):
    for delta in range(-5, 6):
        Y = X + datetime.timedelta(days=delta)
        if base_start <= Y <= base_end:
            d = doy_from_date(Y)
            if d != 60:
                doy_to_indices[d].append(i)

print(f"Built doy-to-indices mapping: {len(doy_to_indices)} doys")

# Compute thresholds and climatologies in float64 using vectorized operations
n_lat, n_lon = baseline_sst.shape[1], baseline_sst.shape[2]
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

compute_start = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    idx_d = d - 1
    indices = doy_to_indices[d]
    pool_data = baseline_sst[indices]  # (121, 60, 60) in float64
    
    # Compute percentile and mean ignoring NaN
    with np.errstate(all='ignore'):
        threshold[idx_d] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
        climatology[idx_d] = np.nanmean(pool_data, axis=0)

compute_elapsed = time.time() - compute_start
print(f"Computed thresholds and climatologies in {compute_elapsed:.1f}s")

# Set day 60 to mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Apply 31-day smoothing
def smooth_31day(arr):
    ext = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    result = np.zeros_like(arr)
    for d in range(366):
        result[d] = np.mean(ext[d:d+31], axis=0)
    return result

threshold_smooth = smooth_31day(threshold)
climatology_smooth = smooth_31day(climatology)

elapsed = time.time() - start
print(f"Total computation time: {elapsed:.1f}s")

# Verify no NaN in smoothed arrays for sea cells
sea_cells = np.load('/tmp/sea_cells.npy')
thr_nan = np.isnan(threshold_smooth).sum()
clim_nan = np.isnan(climatology_smooth).sum()
print(f"NaN in smoothed threshold: {thr_nan}")
print(f"NaN in smoothed climatology: {clim_nan}")

# Save
np.save('/tmp/threshold_smooth_v2.npy', threshold_smooth)
np.save('/tmp/climatology_smooth_v2.npy', climatology_smooth)
print("Saved smoothed thresholds and climatologies (float64)")

# Compare with original float32 computation
threshold_orig = np.load('/tmp/threshold_smooth.npy')
climatology_orig = np.load('/tmp/climatology_smooth.npy')
print(f"\nMax diff in threshold: {np.nanmax(np.abs(threshold_smooth - threshold_orig)):.10f}")
print(f"Max diff in climatology: {np.nanmax(np.abs(climatology_smooth - climatology_orig)):.10f}")
