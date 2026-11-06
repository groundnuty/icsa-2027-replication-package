
import numpy as np
import datetime

# Load data
baseline_vals = np.load('baseline_vals.npy')  # (4028, 60, 60) float32
target_vals = np.load('target_vals.npy')  # (92, 60, 60) float32
baseline_dates_str = np.load('baseline_dates.npy', allow_pickle=True)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
lat_vals = np.load('lat_vals.npy')
lon_vals = np.load('lon_vals.npy')

baseline_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in baseline_dates_str]
target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

# Day of year mapping
def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Convert to float64
baseline_vals = baseline_vals.astype(np.float64)
target_vals = target_vals.astype(np.float64)

# Step 1: Determine sea cells
target_finite = np.isfinite(target_vals)  # (92, 60, 60)
sea_cells = np.all(target_finite, axis=0)  # (60, 60)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# Month-day mapping
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def doy_to_md(doy):
    cum = 0
    for m in range(12):
        if doy <= cum + month_days[m]:
            return m + 1, doy - cum
        cum += month_days[m]
    raise ValueError(f"Invalid doy: {doy}")

def is_valid_date(y, m, d):
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False

# Build pool indices for each day of year
all_dates = baseline_dt
pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    m, dd = doy_to_md(d)
    
    baseline_dates_for_d = []
    for y in range(1992, 2003):
        if is_valid_date(y, m, dd):
            baseline_dates_for_d.append(datetime.datetime(y, m, dd))
    
    idx_set = set()
    for D in baseline_dates_for_d:
        for delta in range(-5, 6):
            X = D + datetime.timedelta(days=delta)
            if X >= all_dates[0] and X <= all_dates[-1]:
                idx = (X - all_dates[0]).days
                idx_set.add(idx)
    
    pool_indices[d] = sorted(idx_set)

# Compute threshold and climatology for each day and each sea cell
nlat, nlon = 60, 60
sea_indices = np.where(sea_cells)

# Use arrays of size 367 to index by day of year directly (index 0 unused)
threshold = np.full((367, 60, 60), np.nan)
climatology = np.full((367, 60, 60), np.nan)

sea_lat_idx = sea_indices[0]
sea_lon_idx = sea_indices[1]
n_sea = len(sea_lat_idx)

# For each day of year, compute for each sea cell
for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    vals = baseline_vals[idx]  # (len(idx), 60, 60)
    
    for k in range(n_sea):
        lat_i, lon_i = sea_lat_idx[k], sea_lon_idx[k]
        cell_vals = vals[:, lat_i, lon_i]
        cell_vals = cell_vals[np.isfinite(cell_vals)]
        if len(cell_vals) == 0:
            continue
        threshold[d, lat_i, lon_i] = np.percentile(cell_vals, 90, method='hazen')
        climatology[d, lat_i, lon_i] = np.mean(cell_vals)

print("Computed threshold and climatology for days 1-366 (except 60)")

# Set day 60 to mean of days 59 and 61
for k in range(n_sea):
    lat_i, lon_i = sea_lat_idx[k], sea_lon_idx[k]
    threshold[60, lat_i, lon_i] = (threshold[59, lat_i, lon_i] + threshold[61, lat_i, lon_i]) / 2
    climatology[60, lat_i, lon_i] = (climatology[59, lat_i, lon_i] + climatology[61, lat_i, lon_i]) / 2

print("Set day 60 as mean of days 59 and 61")

# Check for NaN in sea cells
threshold_sea = threshold[1:367, sea_cells]
clim_sea = climatology[1:367, sea_cells]
print(f"NaN in threshold (sea cells): {np.isnan(threshold_sea).sum()}")
print(f"NaN in climatology (sea cells): {np.isnan(clim_sea).sum()}")

# Save intermediate results
np.save('threshold_raw.npy', threshold)
np.save('climatology_raw.npy', climatology)
np.save('sea_cells.npy', sea_cells)
