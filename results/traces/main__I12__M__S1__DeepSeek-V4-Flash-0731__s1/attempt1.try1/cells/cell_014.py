
import numpy as np

# Load baseline data
baseline_data = np.load('/tmp/baseline_data.npy')
n_dates, n_lat, n_lon = baseline_data.shape

from datetime import date, timedelta

def day_of_year(d):
    month = d.month
    day = d.day
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    if month > 2:
        doy += 1
    return doy

# Rebuild pool indices
base_start = date(1991, 12, 27)
base_end = date(2003, 1, 5)
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {d: i for i, d in enumerate(base_dates)}

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy not in baseline_by_doy:
        baseline_by_doy[doy] = []
    baseline_by_doy[doy].append(d)
    d += timedelta(days=1)

pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    idx_list = []
    for bd in baseline_by_doy.get(doy, []):
        for i in range(-5, 6):
            cd = bd + timedelta(days=i)
            idx_list.append(date_to_idx[cd])
    pool_indices[doy] = np.array(idx_list, dtype=np.int32)

# Compute threshold (90th percentile, Hazen method) and climatology (mean) for each cell and doy
threshold = np.zeros((366, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((366, n_lat, n_lon), dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pool_indices[doy]
    pool = baseline_data[idx]  # shape (121, 60, 60)
    # Convert to float64
    pool64 = pool.astype(np.float64)
    
    # Compute mean ignoring NaN
    climatology[doy-1] = np.nanmean(pool64, axis=0)
    
    # Compute 90th percentile using Hazen method, ignoring NaN
    # For each cell, we need the 90th percentile of non-NaN values
    # np.percentile with method='hazen'
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool64[:, i, j]
            vals = vals[~np.isnan(vals)]
            if len(vals) > 0:
                threshold[doy-1, i, j] = np.percentile(vals, 90, method='hazen')
            else:
                threshold[doy-1, i, j] = np.nan

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

print("Threshold shape:", threshold.shape)
print("Climatology shape:", climatology.shape)

# Check some values
print("\nSample threshold for cell (30,30):")
for doy in [58, 59, 60, 61, 152, 244]:
    print(f"  Day {doy+1}: {threshold[doy, 30, 30]:.4f}")

print("\nSample climatology for cell (30,30):")
for doy in [58, 59, 60, 61, 152, 244]:
    print(f"  Day {doy+1}: {climatology[doy, 30, 30]:.4f}")

np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
print("Saved raw threshold and climatology")
