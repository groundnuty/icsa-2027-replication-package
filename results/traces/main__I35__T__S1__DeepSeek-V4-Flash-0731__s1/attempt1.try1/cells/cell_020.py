
import numpy as np
import datetime
from collections import defaultdict

# Load data
baseline_sst = np.load('/tmp/baseline_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/tmp/target_sst.npy')       # (92, 60, 60)
baseline_times = np.load('/tmp/baseline_times.npy')
target_times = np.load('/tmp/target_times.npy')

baseline_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in baseline_times]
target_dates = [np.datetime64(t).astype('datetime64[D]').astype(object) for t in target_times]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return days_before[month-1] + day

# Build date->index mapping
baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Identify sea cells
n_time, n_lat, n_lon = target_sst.shape
sea_mask = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        sea_mask[i,j] = np.all(np.isfinite(target_sst[:, i, j]))

# Build day-of-year pools
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

doy_dates = defaultdict(list)
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    doy_dates[doy].append(d)
    d += datetime.timedelta(days=1)

doy_pool_indices = {}
for doy, dates in doy_dates.items():
    if doy == 60:
        continue
    pool_dates = set()
    for D in dates:
        for offset in range(-5, 6):
            pool_dates.add(D + datetime.timedelta(days=offset))
    indices = []
    for pd in sorted(pool_dates):
        if pd in baseline_date_to_idx:
            indices.append(baseline_date_to_idx[pd])
    doy_pool_indices[doy] = indices

# Now compute thresholds and climatology for each sea cell and day-of-year
# For efficiency, we process all cells at once per day-of-year

n_lat, n_lon = 60, 60
n_doy = 366

# Initialize arrays
threshold = np.zeros((n_doy, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((n_doy, n_lat, n_lon), dtype=np.float64)

# For each doy (except 60), compute threshold and climatology
for doy in range(1, n_doy + 1):
    if doy == 60:
        continue
    idx = doy_pool_indices[doy]
    # Extract pool values for all cells: (len(idx), n_lat, n_lon)
    pool = baseline_sst[idx, :, :]  # shape (n_pool, 60, 60)
    
    # Compute mean ignoring NaN
    with np.errstate(all='ignore'):
        clim = np.nanmean(pool, axis=0)  # (60, 60)
    
    # Compute 90th percentile using numpy method="hazen"
    # Need to handle NaN values - ignore them
    # For each cell, extract non-NaN values and compute percentile
    # We need to do this per cell since different cells have different NaN patterns
    
    pct = np.zeros((n_lat, n_lon), dtype=np.float64)
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool[:, i, j]
            vals = vals[np.isfinite(vals)]
            if len(vals) > 0:
                pct[i, j] = np.percentile(vals, 90, method='hazen')
            else:
                pct[i, j] = np.nan
    
    threshold[doy-1, :, :] = pct
    climatology[doy-1, :, :] = clim

# Set day 60 to mean of days 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

print("Computed raw thresholds and climatology")
print(f"Threshold shape: {threshold.shape}")
print(f"Climatology shape: {climatology.shape}")
print(f"Threshold sample (doy 153, first few cells): {threshold[152, 0, :5]}")
print(f"Climatology sample (doy 153, first few cells): {climatology[152, 0, :5]}")

# Save intermediate results
np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
print("Saved raw thresholds and climatology")
