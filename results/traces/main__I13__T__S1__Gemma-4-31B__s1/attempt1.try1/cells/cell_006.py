import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import xarray as xr
import json

def get_doy(date):
    # date is a datetime object or pd.Timestamp
    doy = date.timetuple().tm_yday
    is_leap = (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0))
    if not is_leap and doy >= 60:
        doy += 1
    return doy

def smooth_array(arr):
    # 31-day moving mean, centered, wrap around
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # window: d-15 to d+15
        window = []
        for i in range(-15, 16):
            idx = (d + i) % 366
            window.append(arr[idx])
        smoothed[d] = np.mean(window)
    return smoothed

# 1. Sea cells
# Target SST is (92, 60, 60). 
# Sea cells: SST is finite on every day of the target period.
# finite = not nan and not inf
is_sea_cell = np.all(np.isfinite(target_sst), axis=0)
sea_cells_mask = is_sea_cell # Shape (60, 60)

# 2. Threshold and climatology
# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_dates_pd = pd.date_range(baseline_start, baseline_end)

# Mapping baseline SST indices to dates
# baseline_sst was loaded from 1991-12-27 to 2003-01-05
all_baseline_dates = pd.date_range(datetime(1991, 12, 27), datetime(2003, 1, 5))
date_to_idx = {date: i for i, date in enumerate(all_baseline_dates)}

# Pre-calculate DOY for all dates in the loaded baseline
all_baseline_doys = np.array([get_doy(d) for d in all_baseline_dates])

# Result arrays: (366, 60, 60)
thresholds = np.full((366, 60, 60), np.nan, dtype=np.float64)
climatology = np.full((366, 60, 60), np.nan, dtype=np.float64)

# For each day of year d (1 to 366)
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool: SST values within +/- 5 calendar days of any baseline date whose DOY is d.
    # Find all baseline dates with DOY == d
    baseline_dates_with_doy_d = all_baseline_dates[all_baseline_doys == d]
    
    # For each such date, the window is [date-5, date+5]
    # We need to collect all unique dates in these windows.
    pool_dates = set()
    for bd in baseline_dates_with_doy_d:
        for offset in range(-5, 6):
            window_date = bd + timedelta(days=offset)
            if window_date in date_to_idx:
                pool_dates.add(window_date)
    
    if not pool_dates:
        continue
        
    pool_indices = [date_to_idx[date] for date in pool_dates]
    pool_data = baseline_sst[pool_indices, :, :] # (num_dates, 60, 60)
    
    # Compute percentile and mean per cell
    # numpy.nanpercentile can be used. For method="hazen", we use np.quantile with method="hazen"
    # np.quantile does not ignore NaNs, so we use nanquantile if available or mask.
    # np.nanquantile is available in newer numpy.
    
    # To avoid memory issues or slow computation, we can loop over cells or use axis
    # However, we only care about sea cells.
    
    # Since we need double precision, and we are using float64, we are good.
    # The 90th percentile (quantile 0.9)
    
    # Efficient way to compute quantile and mean along axis 0
    # We use np.nanpercentile which is equivalent to nanquantile
    thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
    climatology[d-1] = np.nanmean(pool_data, axis=0)

# Day 60: mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day moving mean (centered, wraps around)
# thresholds and climatology are (366, 60, 60)
smoothed_thresholds = np.full_like(thresholds)
smoothed_climatology = np.full_like(climatology)

for i in range(60):
    for j in range(60):
        smoothed_thresholds[:, i, j] = smooth_array(thresholds[:, i, j])
        smoothed_climatology[:, i, j] = smooth_array(climatology[:, i, j])

# 3. Per-cell MHWs
# target_sst: (92, 60, 60)
# target_dates: 2021-06-01 to 2021-08-31
target_doys = np.array([get_doy(d) for d in target_dates])
# Convert 1-based DOY to 0-based index
target_doy_indices = target_doys - 1

mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

for i in range(60):
    for j in range(60):
        if not sea_cells_mask[i, j]:
            continue
            
        sst_cell = target_sst[:, i, j]
        thresh_cell = smoothed_thresholds[target_doy_indices, i, j]
        
        # a day is hot if SST >= threshold
        hot = (sst_cell >= thresh_cell)
        
        # Find MHWs: run of >= 5 consecutive hot days, join gaps of 1-2 non-hot days
        # This is basically a morphological closing with a kernel of 3, then filtering by length.
        # No, the "join gaps" happens AFTER identifying hot days? 
        # "a per-cell MHW is a run of at least 5 consecutive hot days; 
        # per-cell MHWs separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it."
        
        # Let's implement this precisely:
        # 1. Find all runs of >= 5 hot days.
        # 2. Join these runs if they are separated by 1 or 2 days.
        
        # Easier:
        # 1. Identify all hot days.
        # 2. Create an initial mask of "in an MHW" by finding runs of >= 5.
        # 3. Then join these MHWs.
        # Wait, if I join two runs of 5 with a gap of 2, the gap is now part of the MHW.
        
        # Let's do it iteratively or using a simple loop.
        
        is_mhw = np.zeros(len(hot), dtype=bool)
        # Find initial MHWs
        current_run = 0
        start_idx = 0
        for k in range(len(hot)):
            if hot[k]:
                if current_run == 0:
                    start_idx = k
                current_run += 1
            else:
                if current_run >= 5:
                    is_mhw[start_idx : start_idx + current_run] = True
                current_run = 0
        if current_run >= 5:
            is_mhw[start_idx : start_idx + current_run] = True
            
        # Now join gaps of 1 or 2 non-hot days between MHWs.
        # Repeat until no more joins can be made.
        changed = True
        while changed:
            changed = False
            # Find gaps of 1 or 2 between True values
            # A gap of 1 at k means is_mhw[k-1] and is_mhw[k+1] are True
            for k in range(1, len(is_mhw) - 1):
                if not is_mhw[k] and is_mhw[k-1] and is_mhw[k+1]:
                    is_mhw[k] = True
                    changed = True
            # A gap of 2 at k, k+1 means is_mhw[k-1] and is_mhw[k+2] are True
            for k in range(1, len(is_mhw) - 2):
                if not is_mhw[k] and not is_mhw[k+1] and is_mhw[k-1] and is_mhw[k+2]:
                    is_mhw[k] = True
                    is_mhw[k+1] = True
                    changed = True
        
        mhw_mask[:, i, j] = is_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW event: maximal run of consecutive active days
events = []
current_event_start = None
for k in range(len(active_days)):
    if active_days[k]:
        if current_event_start is None:
            current_event_start = k
    else:
        if current_event_start is not None:
            events.append({
                "onset": target_dates[current_event_start].strftime('%Y-%m-%d'),
                "end": target_dates[k-1].strftime('%Y-%m-%d')
            })
            current_event_start = None
if current_event_start is not None:
    events.append({
        "onset": target_dates[current_event_start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Save results
# mhw_mask is (92, 60, 60)
# We need to create a NetCDF with coordinates
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={
        "time": target_dates,
        "lat": lats,
        "lon": lons
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {
        "start": target_dates[0].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Analysis complete.")
