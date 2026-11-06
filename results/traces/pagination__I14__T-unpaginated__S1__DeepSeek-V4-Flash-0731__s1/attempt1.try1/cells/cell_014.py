
import numpy as np
from datetime import date, timedelta

# Load the baseline data
baseline_sst = np.load('baseline_sst.npy')
sea_mask = np.load('sea_mask.npy')

def day_of_year_fixed(y, m, d):
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

full_range_start = date(1991, 12, 27)
full_range_end = date(2003, 1, 5)
all_dates = []
d = full_range_start
while d <= full_range_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_dates_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year_fixed(d.year, d.month, d.day)
    if doy != 60:
        if doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[doy] = []
        baseline_dates_by_doy[doy].append(d)
    d += timedelta(days=1)

pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for bd in baseline_dates_by_doy.get(doy, []):
        for offset in range(-5, 6):
            nd = bd + timedelta(days=offset)
            if full_range_start <= nd <= full_range_end:
                indices.add(date_to_idx[nd])
    pool_indices[doy] = sorted(indices)

print("Pool indices built")

# Use 0-based indexing: index = doy - 1
# threshold[365, 60, 60] for days 1-366
threshold = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
print(f"Number of sea cells: {n_sea}")

# For each day of year, compute threshold and climatology for each sea cell
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pool_indices[doy]
    if len(idx) == 0:
        continue
    pool_data = baseline_sst[idx].astype(np.float64)
    
    for ci, (lat_i, lon_i) in enumerate(sea_cells):
        values = pool_data[:, lat_i, lon_i]
        finite_vals = values[np.isfinite(values)]
        if len(finite_vals) > 0:
            threshold[doy-1, lat_i, lon_i] = np.quantile(finite_vals, 0.9, method='hazen')
            climatology[doy-1, lat_i, lon_i] = np.mean(finite_vals)
    
    if doy % 50 == 0:
        print(f"Processed day-of-year {doy}")

print("Thresholds and climatologies computed")

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
for ci, (lat_i, lon_i) in enumerate(sea_cells):
    threshold[59, lat_i, lon_i] = (threshold[58, lat_i, lon_i] + threshold[60, lat_i, lon_i]) / 2
    climatology[59, lat_i, lon_i] = (climatology[58, lat_i, lon_i] + climatology[60, lat_i, lon_i]) / 2

print("Day 60 set to mean of days 59 and 61")

np.save('threshold_raw.npy', threshold)
np.save('climatology_raw.npy', climatology)
print("Saved raw thresholds and climatologies")
