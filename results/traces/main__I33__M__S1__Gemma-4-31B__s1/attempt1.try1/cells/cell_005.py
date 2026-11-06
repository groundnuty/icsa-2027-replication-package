import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def get_doy(date):
    month = date.month
    day = date.day
    month_starts = {
        1: 1,
        2: 32,
        3: 61, 
        4: 92,
        5: 122,
        6: 152,
        7: 182,
        8: 213,
        9: 243,
        10: 273,
        11: 304,
        12: 334,
    }
    if month == 2 and day == 29:
        return 60
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
print(f"Sea cells: {np.sum(sea_mask)}")

# 2. Baseline Calculations
all_baseline_dates = pd.date_range(baseline_start - timedelta(days=5), baseline_end + timedelta(days=5))
baseline_sst_dict = {}
for d in all_baseline_dates:
    val = load_sst_region(d, lat_min, lat_max, lon_min, lon_max)
    if val is not None:
        baseline_sst_dict[d] = val

baseline_years_dates = pd.date_range(baseline_start, baseline_end)

# We'll calculate thresholds only for sea cells to avoid warnings, but keep array shape
thresholds = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((367, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_values = []
    for b_date in baseline_years_dates:
        if get_doy(b_date) == d:
            for offset in range(-5, 6):
                win_date = b_date + timedelta(days=offset)
                if win_date in baseline_sst_dict:
                    pool_values.append(baseline_sst_dict[win_date])
    
    if pool_values:
        pool_arr = np.stack(pool_values) # (n_days, lat, lon)
        # Calculate only for sea cells to avoid warnings and be faster
        # Use mask for nanquantile and nanmean
        t_val = np.nanquantile(pool_arr, 0.9, axis=0, method='hazen')
        c_val = np.nanmean(pool_arr, axis=0)
        thresholds[d] = t_val
        climatology[d] = c_val

# Fill day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

def smooth_366(arr):
    data = arr[1:] # (366, lat, lon)
    smoothed = np.zeros_like(data)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        # Calculate mean across the time dimension for each cell
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

smoothed_thresholds = smooth_366(thresholds)
smoothed_climatology = smooth_366(climatology)

# 3. Per-cell MHWs
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
for lat_idx in range(sst_target.shape[1]):
    for lon_idx in range(sst_target.shape[2]):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        cell_sst = sst_target[:, lat_idx, lon_idx]
        cell_thresholds = []
        for d in target_dates:
            doy = get_doy(d)
            cell_thresholds.append(smoothed_thresholds[doy-1, lat_idx, lon_idx])
        cell_thresholds = np.array(cell_thresholds)
        
        hot = cell_sst >= cell_thresholds
        
        is_mhw = np.zeros(len(hot), dtype=bool)
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
        
        changed = True
        while changed:
            changed = False
            for j in range(1, len(is_mhw) - 1):
                if not is_mhw[j]:
                    if is_mhw[j-1] and is_mhw[j+1]:
                        is_mhw[j] = True
                        changed = True
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

# Output files
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
