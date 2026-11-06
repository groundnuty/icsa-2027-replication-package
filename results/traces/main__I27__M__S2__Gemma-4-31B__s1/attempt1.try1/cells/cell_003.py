import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Parameters
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61
TARGET_START = "2008-06-01"
TARGET_END = "2008-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_doy(date):
    """Maps a date to a day of year from 1 to 366."""
    # Use a fixed mapping as per instructions: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61
    # Non-leap years have no day 60.
    if date.month == 1:
        return date.day
    if date.month == 2:
        if date.day <= 28:
            return 31 + date.day
        else: # 29th
            return 60
    # For months after February, we need to know if it's a leap year to decide if Feb 29 existed.
    # But the instructions say: "Map every date to a day of year from 1 to 366 by month and day:
    # 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366."
    # This implies a fixed mapping regardless of leap year.
    # Let's use a fixed array of days in months for a leap year.
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # If not a leap year and date is March 1, should it be 60 or 61?
    # "Non-leap years have no day 60."
    # This means if it's not a leap year, we skip 60.
    # Let's re-read: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # This suggests a fixed mapping:
    # Jan: 1-31
    # Feb: 32-59 (28), 60 (29)
    # Mar: 61-91
    # ...
    # This is exactly what happens in a leap year.
    # For a non-leap year, Feb 29 simply doesn't occur.
    # So we can just use the leap year mapping for all.
    return sum(days_in_months[:date.month - 1]) + date.day

# Load dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine="h5netcdf")

# Region slicing
lat_idx = np.where((ds.latitude.values >= LAT_MIN) & (ds.latitude.values <= LAT_MAX))[0]
lon_idx = np.where((ds.longitude.values >= LON_MIN) & (ds.longitude.values <= LON_MAX))[0]
ds_region = ds.isel(latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1))

# Target period slicing
target_ds = ds_region.sel(time=slice(TARGET_START, TARGET_END))
target_times = target_ds.time.values
target_sst = target_ds.analysed_sst.values.astype(np.float64)

# Sea cells: finite SST on every day of the target period
# target_sst shape: (time, lat, lon)
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells_mask = is_finite # (lat, lon)

# Baseline Period
baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
# Extended range for windows
extended_start = pd.Timestamp(BASELINE_START) - pd.Timedelta(days=5)
extended_end = pd.Timestamp(BASELINE_END) + pd.Timedelta(days=5)
extended_dates = pd.date_range(extended_start, extended_end)

# Pre-calculate DOY for all dates in dataset for the region
# To make it efficient, slice the dataset for the extended range
baseline_ext_ds = ds_region.sel(time=slice(extended_start.strftime('%Y-%m-%d'), extended_end.strftime('%Y-%m-%d')))
baseline_ext_sst = baseline_ext_ds.analysed_sst.values.astype(np.float64)
baseline_ext_times = baseline_ext_ds.time.values

# Create a mapping from date to index in baseline_ext_sst
date_to_idx = {np.datetime64(d).astype('datetime64[ns]'): i for i, d in enumerate(baseline_ext_times)}

# Baseline range indices
base_range_dates = pd.date_range(BASELINE_START, BASELINE_END)
base_range_indices = [date_to_idx[np.datetime64(d).astype('datetime64[ns]')] for d in base_range_dates]

# Pools for each day of year
thresholds = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)

# Pre-calculate DOY for all baseline range dates
base_doy = np.array([get_doy(d.to_pydatetime()) for d in base_range_dates])

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find baseline dates with DOY d
    matching_indices = np.where(base_doy == d)[0]
    if len(matching_indices) == 0:
        continue
        
    # For each such date, find the window +/- 5 days in the extended range
    pool_indices = set()
    for idx in matching_indices:
        # The date at this index
        date = base_range_dates[idx]
        # Window dates
        for offset in range(-5, 6):
            win_date = date + pd.Timedelta(days=offset)
            win_date_np = np.datetime64(win_date).astype('datetime64[ns]')
            if win_date_np in date_to_idx:
                pool_indices.add(date_to_idx[win_date_np])
    
    pool_indices = list(pool_indices)
    # Extract SST values for these indices: (len(pool_indices), lat, lon)
    pool_sst = baseline_ext_sst[pool_indices, :, :]
    
    # Compute threshold (90th percentile, hazen) and climatology (mean)
    # numpy.quantile with method="hazen" is Hyndman-Fan type 5
    # Note: np.nanquantile is available
    thresholds[d-1] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrap around
def smooth(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # Days d-15 to d+15 modulo 366
        indices = [(d - 15 + i) % 366 for i in range(31)]
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds_smoothed = smooth(thresholds)
climatologies_smoothed = smooth(climatologies)

# Per-cell MHWs
# Target SST: (time, lat, lon)
# Thresholds: (366, lat, lon)
target_doy = np.array([get_doy(pd.Timestamp(t).to_pydatetime()) for t in target_times])
# Map target_doy to indices 0-365
target_doy_idx = target_doy - 1

# hot_mask: (time, lat, lon)
# We need to broadcast thresholds_smoothed[target_doy_idx] to (time, lat, lon)
# thresholds_smoothed is (366, lat, lon)
# thresholds_at_target is (time, lat, lon)
thresholds_at_target = thresholds_smoothed[target_doy_idx]
hot_mask = target_sst >= thresholds_at_target

# Now apply MHW rules per cell
mhw_mask = np.zeros(hot_mask.shape, dtype=np.uint8)
lat_size, lon_size = ds_region.latitude.size, ds_region.longitude.size

for i in range(lat_size):
    for j in range(lon_size):
        if not sea_cells_mask[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Find runs of at least 5 hot days
        # A simple way: find all hot segments
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot) - 1))
        
        # Join gaps of 1 or 2 non-hot days
        if not runs:
            continue
            
        merged_runs = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end <= 3: # gap is next_start - curr_end - 1
                    # gap size 1: next_start - curr_end = 2
                    # gap size 2: next_start - curr_end = 3
                    # Wait, gap is days between.
                    # If curr_end is 10 and next_start is 12, gap is day 11 (size 1).
                    # If curr_end is 10 and next_start is 13, gap is days 11, 12 (size 2).
                    # So gap size = next_start - curr_end - 1.
                    # Gap size <= 2  =>  next_start - curr_end <= 3.
                    curr_end = next_end
                else:
                    merged_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged_runs.append((curr_start, curr_end))
            
        for start, end in merged_runs:
            cell_mhw[start:end+1] = True
            
        mhw_mask[:, i, j] = cell_mhw.astype(np.uint8)

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((target_times[start], target_times[t-1]))
            start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

# Format regional events for report
events_list = [{"onset": np.datetime64(start).astype('datetime64[D]').astype(str), 
                "end": np.datetime64(end).astype('datetime64[D]').astype(str)} 
               for start, end in regional_events]

# Save mhw_mask.nc
# Create a dataset with the correct coordinates
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_times, "latitude": ds_region.latitude, "longitude": ds_region.longitude}
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

# Save report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": events_list,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
