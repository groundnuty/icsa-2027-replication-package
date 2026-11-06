
import numpy as np
import pandas as pd

# Load saved data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')  # (366, 60, 60)
climatology_smooth = np.load('/work/climatology_smooth.npy')  # (366, 60, 60)
sea_cells = np.load('/work/sea_cells.npy')  # (60, 60)

# Load target data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_times = target_data.time.values
target_data64 = target_data.values.astype(np.float64)  # (92, 60, 60)

# Target day of year
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

# For each target day, get the threshold for each cell
# thresholds_smooth[doy-1, lat, lon]
# We need to extract the threshold for each target day
# threshold_for_target[t, lat, lon] = thresholds_smooth[target_doy[t]-1, lat, lon]

# Use advanced indexing
threshold_for_target = thresholds_smooth[target_doy - 1, :, :]  # (92, 60, 60)

# Hot days: SST >= threshold
hot = target_data64 >= threshold_for_target  # (92, 60, 60)

# Only consider sea cells; for non-sea cells, set hot to False
hot[~sea_cells] = False

# For sea cells that have NaN in target data (shouldn't happen by definition),
# but just in case
hot = hot & np.isfinite(target_data64)

print("Hot days shape:", hot.shape)
print("Hot day counts:", hot.sum(axis=0).sum())

# Now for each sea cell, find per-cell MHWs
# A per-cell MHW is a run of >= 5 consecutive hot days
# MHWs separated by 1-2 non-hot days are joined

n_time, n_lat, n_lon = hot.shape
per_cell_mhw = np.zeros_like(hot, dtype=bool)  # (92, 60, 60) - True if in a per-cell MHW

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        
        hot_cell = hot[:, i, j]  # (92,)
        
        # Find runs of consecutive hot days
        runs = []
        start = None
        for t in range(n_time):
            if hot_cell[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t - 1))
                    start = None
        if start is not None:
            runs.append((start, n_time - 1))
        
        # Keep runs with length >= 5
        mhw_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
        
        if not mhw_runs:
            continue
        
        # Merge MHWs separated by 1-2 non-hot days
        merged = [mhw_runs[0]]
        for s, e in mhw_runs[1:]:
            prev_s, prev_e = merged[-1]
            gap = s - prev_e - 1  # number of non-hot days between
            if gap <= 2:
                # Join
                merged[-1] = (prev_s, e)
            else:
                merged.append((s, e))
        
        # Mark days in per-cell MHWs
        for s, e in merged:
            per_cell_mhw[s:e+1, i, j] = True

print("Per-cell MHW cells:", per_cell_mhw.sum())
print("Total per-cell MHW days:", per_cell_mhw.sum())

# Regional events
# A day is active if at least one sea cell is in a per-cell MHW
active_days = np.any(per_cell_mhw, axis=(1, 2))  # (92,)

print("Active days:", active_days.sum())
print("Active day indices:", np.where(active_days)[0])

# Regional MHW events: maximal runs of consecutive active days
events = []
start = None
for t in range(n_time):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t - 1))
            start = None
if start is not None:
    events.append((start, n_time - 1))

print("Regional events:", events)
for s, e in events:
    print(f"  {pd.Timestamp(target_times[s]).date()} to {pd.Timestamp(target_times[e]).date()}")
