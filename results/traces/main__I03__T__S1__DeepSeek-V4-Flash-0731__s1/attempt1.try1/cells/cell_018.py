
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
# Sea cells: SST finite on every day of target period
target_finite = np.isfinite(target_vals)  # (92, 60, 60)
sea_cells = np.all(target_finite, axis=0)  # (60, 60)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# Step 2: Compute threshold and climatology
# For each day of year d (1-366 except 60), and each sea cell, compute threshold and climatology
# from the pool of SST values

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
n_sea = sea_cells.sum()

# Get sea cell indices
sea_indices = np.where(sea_cells)
print(f"Sea cell indices shape: {sea_indices[0].shape}")

# Initialize threshold and climatology arrays (366, 60, 60) but only for sea cells
threshold = np.full((366, 60, 60), np.nan)
climatology = np.full((366, 60, 60), np.nan)

# For each day of year, compute for each sea cell
for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices[d]
    # Extract SST values for these dates for each sea cell
    # baseline_vals[idx] gives (len(idx), 60, 60)
    vals = baseline_vals[idx]  # (len(idx), 60, 60)
    
    # For each sea cell, compute 90th percentile and mean ignoring NaN
    for lat_idx, lon_idx in zip(sea_indices[0], sea_indices[1]):
        cell_vals = vals[:, lat_idx, lon_idx]
        # Remove NaN
        cell_vals = cell_vals[np.isfinite(cell_vals)]
        if len(cell_vals) == 0:
            # No data, keep NaN
            continue
        # 90th percentile using numpy method="hazen" (Hyndman-Fan type 5)
        threshold[d, lat_idx, lon_idx] = np.percentile(cell_vals, 90, method='hazen')
        climatology[d, lat_idx, lon_idx] = np.mean(cell_vals)

print("Computed threshold and climatology for days 1-366 (except 60)")

# Set day 60 to mean of days 59 and 61
for lat_idx, lon_idx in zip(sea_indices[0], sea_indices[1]):
    threshold[60, lat_idx, lon_idx] = (threshold[59, lat_idx, lon_idx] + threshold[61, lat_idx, lon_idx]) / 2
    climatology[60, lat_idx, lon_idx] = (climatology[59, lat_idx, lon_idx] + climatology[61, lat_idx, lon_idx]) / 2

print("Set day 60 as mean of days 59 and 61")
print("Check NaN in threshold:", np.isnan(threshold[sea_cells]).sum())
print("Check NaN in climatology:", np.isnan(climatology[sea_cells]).sum())
