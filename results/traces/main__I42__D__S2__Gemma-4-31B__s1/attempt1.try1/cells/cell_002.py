import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# Setup
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region bounds
lat_min, lat_max = 62.25, 63.45
lon_min, lon_max = 18.73, 19.93

# Time bounds
baseline_start = '1991-12-27'
baseline_end = '2003-01-05'
target_start = '2012-06-01'
target_end = '2012-08-31'

# Slice the dataset for the region first
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Now slice for time
# Since I need both baseline and target, I'll take those separately or just use the range
# to avoid loading too much. But since target is far from baseline, 
# I'll slice twice or just use the whole time range if it's not too large for the region.
# Let's check the size of the region slice.
print(f"Region slice size: {ds_region.analysed_sst.nbytes / 1e6:.2f} MB")

# I will load the SST for the baseline and target periods.
# To be safe and efficient, I'll extract the data as numpy arrays.
sst_baseline = ds_region.analysed_sst.sel(time=slice(baseline_start, baseline_end)).astype('float64').values
time_baseline = pd.to_datetime(ds_region.time.sel(time=slice(baseline_start, baseline_end)).values)

sst_target = ds_region.analysed_sst.sel(time=slice(target_start, target_end)).astype('float64').values
time_target = pd.to_datetime(ds_region.time.sel(time=slice(target_start, target_end)).values)

print(f"Baseline shape: {sst_baseline.shape}, Target shape: {sst_target.shape}")
print(f"Baseline time range: {time_baseline[0]} to {time_baseline[-1]}")
print(f"Target time range: {time_target[0]} to {time_target[-1]}")

# 1. Sea cells: SST is finite on every day of the target period
# sst_target shape is (time, lat, lon)
mask_sea = np.all(np.isfinite(sst_target), axis=0)
print(f"Sea cells count: {np.sum(mask_sea)} out of {mask_sea.size}")

# Coordinate values for the output
lats = ds_region.latitude.values
lons = ds_region.longitude.values

# 2. Threshold and climatology
# Baseline years: 1992-01-01 to 2002-12-31
# For each day of year d (1-366, excluding 60), pool is SST ±5 days of baseline dates with doy=d.
# 29 Feb is doy 60. Non-leap years don't have day 60.

def get_doy(dt):
    # Manual doy calculation to match the specification: 1 Jan = 1, 29 Feb = 60
    # pandas .dayofyear is generally 1-indexed and handles leap years (29 Feb = 60).
    return dt.dayofyear

# Map baseline dates to doy
baseline_doy = np.array([get_doy(t) for t in time_baseline])

# We need a pool for each doy d from 1 to 366 (d != 60).
# For each d, pool = SST values from dates within ±5 calendar days of any date in [1992, 2002] that has doy=d.
# Wait, the rule says: "For each day of year d other than 60, the pool is every SST value 
# whose date lies within ±5 calendar days of a baseline date (1992-01-01 to 2002-12-31) 
# whose day of year is d."

# Let's identify baseline dates (1992-2002) and their doys.
baseline_dates_core = time_baseline[(time_baseline >= '1992-01-01') & (time_baseline <= '2002-12-31')]
core_doy = np.array([get_doy(t) for t in baseline_dates_core])

# For each d in 1..366 (d!=60), find all baseline dates in 1992-2002 with doy=d.
# Then find all indices in time_baseline (1991-12-27 to 2003-01-05) that are within 5 days of those.

thresholds = np.full((366, lats.size, lons.size), np.nan, dtype='float64')
climatologies = np.full((366, lats.size, lons.size), np.nan, dtype='float64')

# Precompute windows for each doy
for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in 1992-2002 with doy == d
    target_dates = baseline_dates_core[core_doy == d]
    
    if len(target_dates) == 0:
        continue
        
    # Find all dates in the full baseline_time (1991-12-27 to 2003-01-05) that are within 5 days of any target_date.
    # Using numpy broadcasting for efficiency
    # baseline_time is (N,) target_dates is (M,)
    # We want any i such that |time_baseline[i] - target_dates[j]| <= 5 days for some j.
    
    # Since the windows are small and repeated, we can just iterate over the target_dates
    # and mark indices.
    mask_pool = np.zeros(len(time_baseline), dtype=bool)
    for td in target_dates:
        # Find range in time_baseline within 5 days
        # time_baseline is sorted
        diff = (time_baseline - td).days
        mask_pool |= (diff >= -5) & (diff <= 5)
    
    pool = sst_baseline[mask_pool] # Shape: (num_days_in_pool, lat, lon)
    
    # Threshold: 90th percentile, method="hazen"
    # np.quantile(..., method='hazen')
    thresholds[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool, axis=0)

# Day 60: mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrapped
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    # result[d] = mean(arr[d-15...d+15])
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        # indices is a list of 31 indices
        # arr[indices] shape: (31, lat, lon)
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

# We need to handle NaNs in the smoothing. The spec says "unweighted centred 31-day moving mean".
# Usually this means ignoring NaNs in the average.
thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period: 2012-06-01 to 2012-08-31
# SST in Kelvin
# Hot if SST >= threshold for that day of year.
target_doy = np.array([get_doy(t) for t in time_target])
# target_doy is (time,)
# thresholds_smoothed is (366, lat, lon)

# Expand target_doy to match thresholds_smoothed
# We want a (time, lat, lon) array of thresholds for the target period.
target_thresholds = thresholds_smoothed[target_doy - 1] # (time, lat, lon)

hot_days = (sst_target >= target_thresholds) # (time, lat, lon)
# Need to account for land cells (sst_target is NaN or not sea)
# The spec says "sea cells are the region's grid cells whose SST is finite on every day of the target period"
# "land cells are 0" in the output mask.
# Let's use the sea mask.
hot_days = np.where(mask_sea, hot_days, False)

# Per-cell MHW: run of >= 5 consecutive hot days.
# Joined if separated by 1 or 2 non-hot days.
mhw_mask = np.zeros(hot_days.shape, dtype=np.uint8)

# We can iterate over each cell
for i in range(lats.size):
    for j in range(lons.size):
        if not mask_sea[i, j]:
            continue
        
        cell_hot = hot_days[:, i, j]
        # Identify runs of hot days
        # A simple way to find runs and join gaps:
        # First, find all hot runs.
        # Then, expand them to include gaps of 1 or 2 days.
        # Finally, keep only those that are at least 5 days long.
        # WAIT: The spec says: "a per-cell MHW is a run of at least 5 consecutive hot days; 
        # per-cell MHWs separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it."
        # This implies:
        # 1. Find "hot runs" (consecutive hot days).
        # 2. Identify "MHW candidates" as hot runs of length >= 5.
        # 3. Join these candidates if they are separated by 1 or 2 days.
        # Let's be careful with the order. 
        # Usually, "a run of at least 5 consecutive hot days" is the basic unit.
        # Let's refine:
        # - Find all hot runs.
        # - Keep those with length >= 5.
        # - Join those keeping gaps of 1-2 days.
        # Let's re-read: "a per-cell MHW is a run of at least 5 consecutive hot days; 
        # per-cell MHWs separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it."
        # This could mean:
        # - a) Define a "potential MHW" as a run of >= 5 hot days.
        # - b) Join these potential MHWs if separated by 1-2 days.
        
        # Let's implement this.
        n_days = len(cell_hot)
        mhw_cell = np.zeros(n_days, dtype=bool)
        
        # Find all runs of hot days
        runs = []
        start = None
        for t in range(n_days):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t - 1))
                    start = None
        if start is not None:
            runs.append((start, n_days - 1))
            
        # Keep runs of length >= 5
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join them
        if not mhw_runs:
            continue
            
        joined = []
        if mhw_runs:
            curr_start, curr_end = mhw_runs[0]
            for i in range(1, len(mhw_runs)):
                next_start, next_end = mhw_runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            joined.append((curr_start, curr_end))
            
        for s, e in joined:
            mhw_cell[s : e + 1] = True
            
        mhw_mask[:, i, j] = mhw_cell.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell of the region is inside a per-cell MHW on that day
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW event: maximal run of consecutive active days
regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((time_target[start], time_target[t-1]))
            start = None
if start is not None:
    regional_events.append((time_target[start], time_target[-1]))

# Formatting dates for report
events_list = [{"onset": d[0].strftime('%Y-%m-%d'), "end": d[1].strftime('%Y-%m-%d')} for d in regional_events]

# Create output NetCDF
out_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": time_target, "latitude": lats, "longitude": lons}
)
out_ds.mhw.attrs['dtype'] = 'uint8'
out_ds.to_netcdf('output/mhw_mask.nc')

# Create report
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": time_baseline[0].strftime('%Y-%m-%d'), "end": time_baseline[-1].strftime('%Y-%m-%d')},
    "target_analysed": {"start": time_target[0].strftime('%Y-%m-%d'), "end": time_target[-1].strftime('%Y-%m-%d')},
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete.")
