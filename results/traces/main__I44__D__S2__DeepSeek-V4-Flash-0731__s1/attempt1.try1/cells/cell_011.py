
import numpy as np
import pandas as pd

# Load saved data
baseline_data = np.load('/work/baseline_data.npy')
target_data = np.load('/work/target_data.npy')
sea_cells = np.load('/work/sea_cells.npy')

print(f"Baseline: {baseline_data.shape}, Target: {target_data.shape}")

# Define day_of_year function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def date_to_doy(dt):
    return doy(dt.month, dt.day)

# Baseline period
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# Extended data period
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')
data_dates = pd.date_range(data_start, data_end, freq='D')

# Build pool dates for each doy
pool_dates = {}
for d in range(1, 367):
    if d == 60:
        continue
    base_dates_d = [dt for dt in baseline_dates if date_to_doy(dt) == d]
    pool = set()
    for t0 in base_dates_d:
        for offset in range(-5, 6):
            t = t0 + pd.Timedelta(days=offset)
            if data_start <= t <= data_end:
                pool.add(t)
    pool_dates[d] = sorted(pool)

# Build index map: data_dates -> position in baseline_data
date_to_pos = {dt: i for i, dt in enumerate(data_dates)}

# For each doy, get the positions in baseline_data
pool_positions = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_positions[d] = [date_to_pos[dt] for dt in pool_dates[d]]

print(f"Pool sizes: min={min(len(v) for v in pool_positions.values())}, max={max(len(v) for v in pool_positions.values())}")

# Compute thresholds and climatology for each cell and doy
# Only for sea cells
n_lat, n_lon = sea_cells.shape
n_doy = 366

# Initialize arrays (for all cells, but we'll only compute for sea cells)
thresholds = np.zeros((n_lat, n_lon, n_doy))
climatology = np.zeros((n_lat, n_lon, n_doy))

# Get indices of sea cells
sea_cell_indices = np.argwhere(sea_cells)
print(f"Computing for {len(sea_cell_indices)} sea cells...")

# For each doy (except 60), compute threshold and climatology
for d in range(1, 367):
    if d == 60:
        continue
    
    # Get pool positions
    positions = pool_positions[d]
    
    # Gather data for these positions
    pool_data = baseline_data[positions]  # shape (n_pool, n_lat, n_lon)
    
    # Compute for each sea cell
    for lat_i, lon_i in sea_cell_indices:
        values = pool_data[:, lat_i, lon_i]
        # Remove NaN
        valid = values[np.isfinite(values)]
        if len(valid) > 0:
            thresholds[lat_i, lon_i, d] = np.percentile(valid, 90, method='hazen')
            climatology[lat_i, lon_i, d] = np.mean(valid)
        else:
            thresholds[lat_i, lon_i, d] = np.nan
            climatology[lat_i, lon_i, d] = np.nan
    
    if d % 30 == 0:
        print(f"  Processed doy {d}")

print("Done computing thresholds and climatology for doys 1-366 (except 60)")

# Set day 60 = mean of days 59 and 61
for lat_i, lon_i in sea_cell_indices:
    thresholds[lat_i, lon_i, 59]  # 0-indexed: doy 60 is index 59
    # Wait, thresholds array is indexed [lat, lon, doy-1] if I use 0-indexed
    # Let me check indexing
    
# Actually, I initialized thresholds as shape (n_lat, n_lon, n_doy) where n_doy=366
# So thresholds[lat, lon, d-1] corresponds to doy d
# Day 60 corresponds to index 59
thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 59] = (
    thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 58] + 
    thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 60]
) / 2

climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 59] = (
    climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 58] + 
    climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 60]
) / 2

print("Day 60 set to mean of days 59 and 61")

# Save intermediate results
np.save('/work/thresholds.npy', thresholds)
np.save('/work/climatology.npy', climatology)
print("Saved thresholds and climatology")
