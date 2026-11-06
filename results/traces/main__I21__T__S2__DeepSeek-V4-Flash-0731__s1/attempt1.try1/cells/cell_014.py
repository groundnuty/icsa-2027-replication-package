
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime

# Load intermediate results
threshold_smooth = np.load('threshold_smooth.npy')
sea_cells = np.load('sea_cells.npy')

# Load target data
target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

# Day of year for target dates
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = [day_of_year(dt) for dt in target_dates]
n_time = len(target_time)
n_lat = target_sst.shape[1]
n_lon = target_sst.shape[2]

# Convert SST to float64
target_sst_f64 = target_sst.astype(np.float64)

# Determine hot days for each cell
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    doy_idx = doy - 1
    for la in range(n_lat):
        for lo in range(n_lon):
            if sea_cells[la, lo]:
                sst_val = target_sst_f64[t, la, lo]
                if np.isfinite(sst_val):
                    thr = threshold_smooth[doy_idx, la, lo]
                    if sst_val >= thr:
                        hot[t, la, lo] = True

# Now detect per-cell MHWs
# For each sea cell, find runs of >= 5 consecutive hot days
# Then join runs separated by 1-2 non-hot days

# mhw_mask: 1 if cell is inside a per-cell MHW on that day
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

sea_indices = np.argwhere(sea_cells)

for la, lo in sea_indices:
    hot_series = hot[:, la, lo]
    
    # Find runs of consecutive hot days
    runs = []  # list of (start_idx, end_idx) inclusive
    i = 0
    while i < n_time:
        if hot_series[i]:
            start = i
            while i < n_time and hot_series[i]:
                i += 1
            end = i - 1
            runs.append((start, end))
        else:
            i += 1
    
    # Join runs separated by 1-2 non-hot days
    if len(runs) <= 1:
        joined_runs = runs
    else:
        joined_runs = [runs[0]]
        for r in runs[1:]:
            prev_end = joined_runs[-1][1]
            gap = r[0] - prev_end - 1
            if gap <= 2:  # 1 or 2 non-hot days between
                joined_runs[-1] = (joined_runs[-1][0], r[1])
            else:
                joined_runs.append(r)
    
    # For each joined run, check if its total length is >= 5 (the original hot run must be >= 5)
    # Wait, re-read the method: "a per-cell MHW is a run of at least 5 consecutive hot days;
    # per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
    
    # So the initial MHW detection requires runs of >= 5 hot days.
    # Then, these MHWs (not all hot runs) separated by 1-2 non-hot days are joined.
    
    # Let me redo this: first find runs of >= 5 hot days as MHWs.
    # Then join MHWs separated by 1-2 non-hot days.
    
    # Find runs of consecutive hot days
    all_runs = []
    i = 0
    while i < n_time:
        if hot_series[i]:
            start = i
            while i < n_time and hot_series[i]:
                i += 1
            end = i - 1
            all_runs.append((start, end))
        else:
            i += 1
    
    # MHWs are runs of >= 5 hot days
    mhws = [(s, e) for s, e in all_runs if (e - s + 1) >= 5]
    
    # Join MHWs separated by 1-2 non-hot days
    if len(mhws) <= 1:
        final_mhws = mhws
    else:
        final_mhws = [mhws[0]]
        for m in mhws[1:]:
            prev_end = final_mhws[-1][1]
            gap = m[0] - prev_end - 1
            if gap <= 2:
                final_mhws[-1] = (final_mhws[-1][0], m[1])
            else:
                final_mhws.append(m)
    
    # Mark the mask
    for s, e in final_mhws:
        mhw_mask[s:e+1, la, lo] = 1

print(f"Total MHW day-cell entries: {np.sum(mhw_mask)}")

# Check how many cells have at least one MHW
cells_with_mhw = np.any(mhw_mask > 0, axis=0)
print(f"Cells with at least one MHW: {np.sum(cells_with_mhw)}")

# Print MHW statistics for a few cells
for la, lo in sea_indices[:5]:
    cell_mhw = mhw_mask[:, la, lo]
    if np.any(cell_mhw):
        # Find MHW runs
        runs = []
        i = 0
        while i < n_time:
            if cell_mhw[i]:
                start = i
                while i < n_time and cell_mhw[i]:
                    i += 1
                runs.append((start, i-1))
            else:
                i += 1
        print(f"Cell ({la},{lo}): {len(runs)} MHW(s)")
        for s, e in runs:
            print(f"  {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e].strftime('%Y-%m-%d')}")

# Save
np.save('mhw_mask.npy', mhw_mask)
print("Saved mhw_mask.")
