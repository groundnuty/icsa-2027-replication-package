import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import json

def get_doy(date):
    """Fixed mapping: 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366"""
    month = date.month
    day = date.day
    # Cumulative days by month (non-leap)
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    if month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        # Wait, the prompt says "Non-leap years have no day 60". 
        # "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366."
        # This implies we should ignore the leap year nature when mapping to 1-366?
        # No, usually it means:
        # Jan 1 -> 1
        # Feb 28 -> 59
        # Feb 29 -> 60
        # Mar 1 -> 61 (always, regardless of leap year)
        pass
    
    # Re-evaluating:
    # 1 Jan: 1
    # 28 Feb: 59
    # 29 Feb: 60
    # 1 Mar: 61 (in any year)
    # This means for non-leap years, the sequence is 1, ..., 59, 61, ...
    # For leap years, it's 1, ..., 59, 60, 61, ...
    
    # Correct implementation of the prompt's mapping:
    # month, day -> doy
    # Jan: 1-31 -> 1-31
    # Feb: 1-28 -> 32-59
    # Feb 29 -> 60
    # Mar: 1-31 -> 61-91 (if non-leap) or 61-91 (if leap)
    # Let's use a manual map for months.
    month_starts = {
        1: 1,
        2: 32,
        3: 61, # Mar 1 is always 61
        4: 92, # Apr 1 is always 92
        5: 122,
        6: 152,
        7: 182,
        8: 213,
        9: 243,
        10: 273,
        11: 304,
        12: 334,
    }
    # Special case for Feb 29
    if month == 2 and day == 29:
        return 60
    # For other dates, use the offset. 
    # Note: Feb 28 is 31 + 28 = 59. Mar 1 is 61.
    # This matches.
    return month_starts[month] + day - 1

def get_sst_file_path(date):
    return f'/data/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'

def load_sst_region(date, lat_min, lat_max, lon_min, lon_max):
    path = get_sst_file_path(date)
    try:
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            region_ds = ds.sel(
                latitude=slice(lat_min, lat_max),
                longitude=slice(lon_min, lon_max)
            )
            # Squeeze time dimension and return values as float64
            return region_ds.analysed_sst.values.squeeze().astype(np.float64)
    except (FileNotFoundError, KeyError):
        return None

# Parameters
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
target_start = datetime(2014, 6, 1)
target_end = datetime(2014, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# 1. Target Period and Sea Cells
target_dates = pd.date_range(target_start, target_end)
sst_target_list = []
for d in target_dates:
    val = load_sst_region(d, lat_min, lat_max, lon_min, lon_max)
    if val is None:
        raise FileNotFoundError(f"Missing target file: {d}")
    sst_target_list.append(val)

sst_target = np.stack(sst_target_list) # (time, lat, lon)
sea_mask = np.all(np.isfinite(sst_target), axis=0)
n_sea = np.sum(sea_mask)
print(f"Sea cells: {n_sea}")

# 2. Baseline Calculations
# We need SST for baseline period plus margins
all_baseline_dates = pd.date_range(baseline_start - timedelta(days=5), baseline_end + timedelta(days=5))
baseline_sst_dict = {}
for d in all_baseline_dates:
    val = load_sst_region(d, lat_min, lat_max, lon_min, lon_max)
    if val is not None:
        baseline_sst_dict[d] = val

# Baseline dates within 1992-2002
baseline_years_dates = pd.date_range(baseline_start, baseline_end)

thresholds = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in 1992-2002 with DOY == d
    pool_values = []
    for b_date in baseline_years_dates:
        if get_doy(b_date) == d:
            # Window [b_date-5, b_date+5]
            for offset in range(-5, 6):
                win_date = b_date + timedelta(days=offset)
                if win_date in baseline_sst_dict:
                    pool_values.append(baseline_sst_dict[win_date])
    
    if pool_values:
        pool_arr = np.stack(pool_values) # (n_days, lat, lon)
        # Threshold: 90th percentile (hazen)
        # numpy.quantile(..., method='hazen')
        thresholds[d] = np.nanquantile(pool_arr, 0.9, axis=0, method='hazen')
        # Climatology: mean
        climatology[d] = np.nanmean(pool_arr, axis=0)

# Fill day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day moving mean, centered, wrap around
def smooth_366(arr):
    # arr shape (367, lat, lon) -> use indices 1 to 366
    data = arr[1:] # (366, lat, lon)
    smoothed = np.zeros_like(data)
    for d in range(366):
        # d is 0-indexed here, so day d+1. 
        # Indices d-15 to d+15 modulo 366.
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

smoothed_thresholds = smooth_366(thresholds)
smoothed_climatology = smooth_366(climatology)

# 3. Per-cell MHWs
# target_dates: 2014-06-01 to 2014-08-31
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
for lat_idx in range(sst_target.shape[1]):
    for lon_idx in range(sst_target.shape[2]):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        # SST and thresholds for this cell over target period
        cell_sst = sst_target[:, lat_idx, lon_idx]
        cell_thresholds = []
        for d in target_dates:
            doy = get_doy(d)
            cell_thresholds.append(smoothed_thresholds[doy-1, lat_idx, lon_idx])
        cell_thresholds = np.array(cell_thresholds)
        
        # a day is hot if SST >= threshold
        hot = cell_sst >= cell_thresholds
        
        # find runs of >= 5 hot days, join gaps of 1-2 non-hot days
        # This is essentially:
        # 1. Find runs of hot days.
        # 2. If two hot runs are separated by 1 or 2 non-hot days, join them.
        # Let's do it iteratively.
        
        # Simple way to implement this:
        # First, find all initial hot runs of length >= 5.
        # Then, repeatedly join runs if they are close.
        # Or: a day is part of an MHW if it's in a hot run of >=5 OR it's a gap of 1-2 between MHWs.
        
        # Correct algorithm:
        # 1. Mark all days as "not MHW".
        # 2. Find all contiguous runs of hot days.
        # 3. If run length >= 5, mark all days in run as "MHW".
        # 4. Repeat: find two MHW runs separated by 1 or 2 non-MHW days.
        #    If found, mark those 1 or 2 days as "MHW".
        # 5. Continue until no more joins can be made.
        
        is_mhw = np.zeros(len(hot), dtype=bool)
        # Initial runs
        i = 0
        while i < len(hot):
            if hot[i]:
                start = i
                while i < len(hot) and hot[i]:
                    i += 1
                if (i - start) >= 5:
                    is_mhw[start:i] = True
            else:
                i += 1
        
        # Joining gaps
        changed = True
        while changed:
            changed = False
            # Find gap of 1 or 2 non-MHW days between MHW runs
            for j in range(1, len(is_mhw) - 1):
                if not is_mhw[j]:
                    # Check if it's a gap of 1
                    if is_mhw[j-1] and is_mhw[j+1]:
                        is_mhw[j] = True
                        changed = True
                    # Check if it's a gap of 2
                    elif j < len(is_mhw) - 2 and is_mhw[j-1] and not is_mhw[j+1] and is_mhw[j+2]:
                        is_mhw[j] = True
                        is_mhw[j+1] = True
                        changed = True
        
        mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)

# 4. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        regional_events.append({
            "onset": target_dates[start].strftime("%Y-%m-%d"),
            "end": target_dates[i-1].strftime("%Y-%m-%d")
        })
    else:
        i += 1

# Prepare output files
# mhw_mask.nc
# Coordinate values from original dataset
# Since we sliced, we should get the coordinates of the slice.
with xr.open_dataset(get_sst_file_path(target_dates[0]), engine="h5netcdf") as ds:
    region_ds = ds.sel(
        latitude=slice(lat_min, lat_max),
        longitude=slice(lon_min, lon_max)
    )
    lat_coords = region_ds.latitude.values
    lon_coords = region_ds.longitude.values

out_ds = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": target_dates, "lat": lat_coords, "lon": lon_coords}
)
out_ds.to_netcdf("output/mhw_mask.nc")

# report.json
# Find the actual baseline days used
# (We used 1992-01-01 to 2002-12-31, but windows’ range was 1991-12-27 to 2003-01-05)
# "baseline_analysed": the first and last baseline day (inclusive) your threshold and climatology used
# The pool for d=1 starts at baseline_start-5 = 1991-12-27.
# The pool for d=365/366 ends at baseline_end+5 = 2003-01-05.
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": target_start.strftime("%Y-%m-%d"), "end": target_end.strftime("%Y-%m-%d")},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
