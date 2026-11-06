import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Setup
fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45
target_start = pd.to_datetime("2016-06-01")
target_end = pd.to_datetime("2016-08-31")
baseline_start_year = 1992
baseline_end_year = 2002

def get_custom_doy(date):
    month_starts = {
        1: 1, 2: 32, 3: 61, 4: 92, 5: 122, 6: 153, 
        7: 183, 8: 214, 9: 245, 10: 275, 11: 306, 12: 336
    }
    return month_starts[date.month] + date.day - 1

def get_file_path(date):
    return f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"

# Get coordinates first
with fs.open(get_file_path(pd.to_datetime("1982-01-01")), "rb") as f:
    ds_coords = xr.open_dataset(f, engine="h5netcdf")
    lats = ds_coords.latitude.values
    lons = ds_coords.longitude.values

lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)
selected_lats = lats[lat_mask]
selected_lons = lons[lon_mask]

def load_sst_region(date):
    path = get_file_path(date)
    with fs.open(path, "rb") as f:
        ds = xr.open_dataset(f, engine="h5netcdf")
        # Squeeze to remove the time dimension (since there is only one)
        return ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), 
                                   longitude=slice(lon_min, lon_max)).squeeze().values.astype(np.float64)

# Target Period Data
target_dates = pd.date_range(target_start, target_end)
target_sst = np.stack([load_sst_region(d) for d in target_dates])
# target_sst shape: (time, lat, lon)

# Identify Sea Cells: SST is finite on every day of the target period
# np.isfinite checks for NaN and Inf
finite_mask = np.all(np.isfinite(target_sst), axis=0) # (lat, lon)
sea_cells = finite_mask

# Baseline Period Range
baseline_pool_start = pd.to_datetime("1991-12-27")
baseline_pool_end = pd.to_datetime("2003-01-05")
baseline_dates = pd.date_range(baseline_pool_start, baseline_pool_end)
baseline_sst_dict = {d: load_sst_region(d) for d in baseline_dates}

# Calculate Threshold and Climatology (per sea cell)
thresholds = np.full((366, len(selected_lats), len(selected_lons)), np.nan)
climatologies = np.full((366, len(selected_lats), len(selected_lons)), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool = []
    for year in range(baseline_start_year, baseline_end_year + 1):
        year_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")
        Dy = None
        for yd in year_dates:
            if get_custom_doy(yd.to_pydatetime()) == d:
                Dy = yd
                break
        
        for offset in range(-5, 6):
            window_date = Dy + timedelta(days=offset)
            if window_date in baseline_sst_dict:
                pool.append(baseline_sst_dict[window_date])
    
    if pool:
        pool_arr = np.stack(pool) # (121, lat, lon)
        # Only compute for sea cells to avoid RuntimeWarnings
        climatologies[d-1][sea_cells] = np.nanmean(pool_arr[:, sea_cells], axis=0)
        thresholds[d-1][sea_cells] = np.nanquantile(pool_arr[:, sea_cells], 0.9, axis=0, method="hazen")

# Day 60: Mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrap around
def smooth_366(arr):
    # arr shape (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices] # (31, lat, lon)
        # Use nanmean across the time dimension (axis=0)
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# Per-cell MHWs
target_doys = [get_custom_doy(d.to_pydatetime()) for d in target_dates]
hot_mask = np.zeros(target_sst.shape, dtype=bool)
for t in range(len(target_dates)):
    doy = target_doys[t]
    # Comparison for all cells; land cells will be NaN in thresholds_smoothed, so result is False
    hot_mask[t] = target_sst[t] >= thresholds_smoothed[doy-1]

mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
num_days, num_lats, num_lons = target_sst.shape

for i in range(num_lats):
    for j in range(num_lons):
        if not sea_cells[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        in_mhw = np.zeros(num_days, dtype=bool)
        
        # Find runs of 5+ hot days
        start = -1
        for t in range(num_days):
            if cell_hot[t]:
                if start == -1:
                    start = t
            else:
                if start != -1:
                    if t - start >= 5:
                        in_mhw[start:t] = True
                    start = -1
        if start != -1 and num_days - start >= 5:
            in_mhw[start:] = True
        
        # Join gaps of 1 or 2 days
        changed = True
        while changed:
            changed = False
            # Gap of 1: 1 0 1 -> 1 1 1
            for t in range(1, num_days - 1):
                if not in_mhw[t] and in_mhw[t-1] and in_mhw[t+1]:
                    in_mhw[t] = True
                    changed = True
            # Gap of 2: 1 0 0 1 -> 1 1 1 1
            for t in range(1, num_days - 2):
                if not in_mhw[t] and not in_mhw[t+1] and in_mhw[t-1] and in_mhw[t+2]:
                    in_mhw[t] = True
                    in_mhw[t+1] = True
                    changed = True
        
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = -1
for t in range(num_days):
    if active_days[t]:
        if start == -1:
            start = t
    else:
        if start != -1:
            regional_events.append({
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[t-1].strftime('%Y-%m-%d')
            })
            start = -1
if start != -1:
    regional_events.append({
        "onset": target_dates[start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Output
os.makedirs('output', exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": target_dates, "lat": selected_lats, "lon": selected_lons}
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_pool_start.strftime('%Y-%m-%d'), "end": baseline_pool_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Analysis complete.")
