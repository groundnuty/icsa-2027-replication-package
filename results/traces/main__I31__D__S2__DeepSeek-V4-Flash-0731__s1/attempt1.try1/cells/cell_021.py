
import numpy as np
import pandas as pd
import xarray as xr

# Load data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_times = target_data.time.values
target_data64 = target_data.values.astype(np.float64)

def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

target_doy = np.array([doy_from_datetime64(t) for t in target_times])
threshold_for_target = thresholds_smooth[target_doy - 1, :, :]

# Hot days
hot = target_data64 >= threshold_for_target
hot = hot & np.broadcast_to(sea_cells, hot.shape)
hot = hot & np.isfinite(target_data64)

# For each cell, check max run length of hot days
n_time, n_lat, n_lon = hot.shape
sea_indices = np.where(sea_cells)

max_runs = []
cells_with_hot = 0
for idx in range(len(sea_indices[0])):
    i, j = sea_indices[0][idx], sea_indices[1][idx]
    hot_cell = hot[:, i, j]
    
    if hot_cell.sum() > 0:
        cells_with_hot += 1
        
    # Find max run
    max_run = 0
    cur_run = 0
    for t in range(n_time):
        if hot_cell[t]:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0
    max_runs.append((i, j, max_run, hot_cell.sum()))

print(f"Cells with at least 1 hot day: {cells_with_hot} out of {len(sea_indices[0])}")
print(f"Max run distribution:")
from collections import Counter
run_counts = Counter([mr[2] for mr in max_runs])
for run_len in sorted(run_counts.keys()):
    print(f"  Max run = {run_len}: {run_counts[run_len]} cells")

# Cells with max run >= 5
cells_with_5 = [(i,j,mr,hs) for i,j,mr,hs in max_runs if mr >= 5]
print(f"\nCells with max run >= 5: {len(cells_with_5)}")

# Show the hottest cells
max_runs_sorted = sorted(max_runs, key=lambda x: -x[2])
print("\nTop 10 cells by max run length:")
for i, j, mr, hs in max_runs_sorted[:10]:
    print(f"  Cell ({i},{j}): max_run={mr}, total_hot={hs}")
    # Show the actual hot days
    hot_days_idx = np.where(hot[:, i, j])[0]
    print(f"    Hot days: {[pd.Timestamp(target_times[t]).strftime('%Y-%m-%d') for t in hot_days_idx]}")
