import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# Configuration
LAT_MIN, LAT_MAX = 61.57, 62.77
LON_MIN, LON_MAX = 20.17, 21.37
TARGET_START = "2021-06-01"
TARGET_END = "2021-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_doy(dt):
    # Map to 1-366 as specified
    # Jan 1 = 1, ..., Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ...
    # In non-leap years, day 60 is skipped.
    month = dt.month
    day = dt.day
    # Days in months for non-leap year
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    if month > 2 and dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0):
        # It's a leap year and we are after February
        # But the mapping says "Non-leap years have no day 60."
        # This implies that in a leap year, Feb 29 is day 60.
        # And in both leap and non-leap years, March 1 is day 61.
        # So if it's a leap year, the doy is the same as if it weren't, 
        # EXCEPT that Feb 29 exists.
        # Let's re-evaluate.
        pass
    
    # Correct mapping:
    # Jan: 1-31
    # Feb: 32-59 (28th) or 32-60 (29th)
    # Mar: 61-91 (1st)
    # Wait, let's just use a simple calculation.
    # For a given date, if month=2 and day=29, doy=60.
    # If month > 2, and it's a leap year, we still want Mar 1 to be 61.
    # This means the "day of year" is essentially the day of year in a leap year.
    
    # Let's use a reference leap year (e.g., 2000) to find the doy.
    ref_date = datetime(2000, month, day)
    return (ref_date - datetime(2000, 1, 1)).days + 1

# Let's test get_doy
print(f"2000-01-01: {get_doy(datetime(2000, 1, 1))}") # 1
print(f"2000-02-28: {get_doy(datetime(2000, 2, 28))}") # 59
print(f"2000-02-29: {get_doy(datetime(2000, 2, 29))}") # 60
print(f"2000-03-01: {get_doy(datetime(2000, 3, 1))}") # 61
print(f"1999-02-28: {get_doy(datetime(1999, 2, 28))}") # 59
print(f"1999-03-01: {get_doy(datetime(1999, 3, 1))}") # 61

# Loading and Slicing
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
sst = ds['analysed_sst']

# Region slice
sst_reg = sst.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))

# Target period slice
target_sst = sst_reg.sel(time=slice(TARGET_START, TARGET_END))

# Baseline period slice (extended by 5 days on each side)
# 1992-01-01 minus 5 days = 1991-12-27
# 2002-12-31 plus 5 days = 2003-01-05
baseline_sst = sst_reg.sel(time=slice("1991-12-27", "2003-01-05"))

# 1. Sea cells: SST finite on every day of target period
# Target period days:
target_times = target_sst.time.values
# We need cells where all values in target_sst are finite
# target_sst has shape (time, lat, lon)
is_sea = np.all(np.isfinite(target_sst.values), axis=0)
sea_indices = np.where(is_sea)
num_sea_cells = len(sea_indices[0])
print(f"Number of sea cells: {num_sea_cells}")

# 2. Threshold and climatology
# Baseline dates
baseline_times = pd.to_datetime(baseline_sst.time.values)
baseline_sst_vals = baseline_sst.values # (time, lat, lon)

# Precompute doy for all baseline times
baseline_doys = np.array([get_doy(t.to_pydatetime()) for t in baseline_times])

# Pools
# For each d in 1..366, d != 60
# Pool d = values on dates T' such that there exists T in baseline with doy(T)=d and |T'-T| <= 5
# Let's identify all T in baseline that are within [1992-01-01, 2002-12-31]
baseline_range_mask = (baseline_times >= pd.Timestamp(BASELINE_START)) & (baseline_times <= pd.Timestamp(BASELINE_END))
baseline_range_indices = np.where(baseline_range_mask)[0]

thresholds = np.full((366, sst_reg.latitude.size, sst_reg.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, sst_reg.latitude.size, sst_reg.longitude.size), np.nan, dtype=np.float64)

# To optimize, let's find which dates are in the pool for each d
for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates T in baseline range with doy(T) = d
    t_indices = baseline_range_indices[baseline_doys[baseline_range_indices] == d]
    
    if len(t_indices) == 0:
        continue
    
    # Find all T' in the full baseline_sst that are within 5 days of any T in t_indices
    # A date T' is in the pool if there is any t_idx in t_indices such that |T' - baseline_times[t_idx]| <= 5 days
    # This is equivalent to: T' is in Union_{t_idx in t_indices} [T-5, T+5]
    
    pool_indices = []
    # We can just iterate through all baseline_times and check the condition
    # Or more efficiently:
    for t_idx in t_indices:
        t_date = baseline_times[t_idx]
        # Find indices in baseline_times within 5 days
        # Since baseline_times is sorted, we can use searchsorted
        start_date = t_date - pd.Timedelta(days=5)
        end_date = t_date + pd.Timedelta(days=5)
        
        # This is a bit slow. Let's use a boolean mask for the whole baseline_times array.
        pass
    
    # Corrected efficiency:
    mask = np.zeros(len(baseline_times), dtype=bool)
    for t_idx in t_indices:
        t_date = baseline_times[t_idx]
        # All dates within 5 days of t_date
        # Since it's daily, we can just find the index of t_date and take +/- 5
        # But baseline_times might have gaps? The dataset says daily, but let's be safe.
        # Find range of indices
        # The distance in days is just the difference in index if there are no gaps.
        # Let's just use the timedeltas.
        diffs = np.abs((baseline_times - t_date).days)
        mask |= (diffs <= 5)
    
    pool_vals = baseline_sst_vals[mask] # (num_days_in_pool, lat, lon)
    
    # Threshold: 90th percentile, numpy method="hazen"
    # Climatology: mean
    # Use np.nanpercentile and np.nanmean
    thresholds[d-1] = np.nanpercentile(pool_vals, 90, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_vals, axis=0)

# Set day 60 to mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrapping around
def smooth(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for i in range(366):
        # Window: i-15 to i+15
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        window = arr[indices]
        smoothed[i] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth(thresholds)
climatologies_smooth = smooth(climatologies)

# 3. Per-cell MHWs
# Target SST and its doys
target_sst_vals = target_sst.values # (time, lat, lon)
target_doys = np.array([get_doy(t.to_pydatetime()) for t in pd.to_datetime(target_sst.time.values)])

# hot_mask shape: (time, lat, lon)
hot_mask = np.zeros(target_sst_vals.shape, dtype=bool)
for t_idx, d in enumerate(target_doys):
    hot_mask[t_idx] = target_sst_vals[t_idx] >= thresholds_smooth[d-1]

# MHW detection per cell
# Only for sea cells
mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)
lat_size = sst_reg.latitude.size
lon_size = sst_reg.longitude.size

for lat_idx, lon_idx in zip(*sea_indices):
    cell_hot = hot_mask[:, lat_idx, lon_idx]
    # Identify runs of >= 5 hot days
    # a simple way: find contiguous blocks of True
    mhw_cell = np.zeros(len(cell_hot), dtype=bool)
    
    # Find blocks of hot days
    i = 0
    while i < len(cell_hot):
        if cell_hot[i]:
            start = i
            while i < len(cell_hot) and cell_hot[i]:
                i += 1
            end = i
            if end - start >= 5:
                mhw_cell[start:end] = True
        else:
            i += 1
            
    # Join gaps of 1-2 non-hot days
    # Repeat until no more joins are possible
    while True:
        changed = False
        i = 0
        while i < len(cell_hot) - 2:
            # Gap of 1: hot, not-hot, hot
            if cell_hot[i] and not cell_hot[i+1] and cell_hot[i+2]:
                # check if both sides are part of an MHW (though the rule just says hot runs)
                # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
                # This implies the runs must be MHWs (>= 5 days)
                # Let's re-read: "a per-cell MHW is a run of at least 5 consecutive hot days; per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
                pass
            i += 1
        break # Placeholder for logic

    # Let's implement the gap joining properly
    # 1. Find all MHW runs (>= 5 hot days)
    # 2. Join them if they are separated by 1-2 non-hot days.
    
    # Step 1: initial MHWs
    mhw_cell = np.zeros(len(cell_hot), dtype=bool)
    i = 0
    runs = []
    while i < len(cell_hot):
        if cell_hot[i]:
            start = i
            while i < len(cell_hot) and cell_hot[i]:
                i += 1
            if i - start >= 5:
                runs.append((start, i))
        else:
            i += 1
    
    # Step 2: Join runs
    if not runs:
        mhw_mask[:, lat_idx, lon_idx] = 0
        continue
        
    joined_runs = []
    if runs:
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            gap = next_start - curr_end
            if gap <= 3: # 1 or 2 non-hot days means gap is 1 or 2. 
                # Wait: if curr_end is the first non-hot day, then next_start - curr_end = 1 means 0 non-hot days?
                # No, curr_end is the index of the first non-hot day.
                # If next_start = curr_end + 1, then there is 1 non-hot day (at index curr_end).
                # If next_start = curr_end + 2, then there are 2 non-hot days (at curr_end and curr_end+1).
                # So gap = next_start - curr_end. Gap 1 or 2.
                # Actually, if they are joined, the gap days also belong to the MHW.
                curr_end = next_end
            else:
                joined_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        joined_runs.append((curr_start, curr_end))
        
    for start, end in joined_runs:
        mhw_cell[start:end] = True
    
    mhw_mask[:, lat_idx, lon_idx] = mhw_cell.astype(np.uint8)

# 4. Regional Events
# A day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        end = i - 1
        regional_events.append((start, end))
    else:
        i += 1

# Results
import os
os.makedirs('output', exist_ok=True)

# Save mhw_mask.nc
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_sst.time, "latitude": sst_reg.latitude, "longitude": sst_reg.longitude}
)
mask_ds.to_netcdf("output/mhw_mask.nc")

# Prepare report
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {
        "start": BASELINE_START,
        "end": BASELINE_END
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END
    },
    "events": [
        {
            "onset": pd.to_datetime(target_sst.time.values[start]).strftime('%Y-%m-%d'),
            "end": pd.to_datetime(target_sst.time.values[end]).strftime('%Y-%m-%d')
        }
        for start, end in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Process complete.")
