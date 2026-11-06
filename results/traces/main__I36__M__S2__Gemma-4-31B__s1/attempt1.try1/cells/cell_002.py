import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

def get_doy(dt):
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    doy = dt.timetuple().tm_yday
    if not is_leap and dt.month >= 3:
        return doy + 1
    return doy

def get_date_from_doy(year, doy):
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    if doy == 60 and not is_leap:
        return None
    if doy <= 59:
        return pd.Timestamp(year, 1, 1) + pd.Timedelta(days=doy-1)
    else:
        standard_doy = doy if is_leap else doy - 1
        return pd.Timestamp(year, 1, 1) + pd.Timedelta(days=standard_doy-1)

LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
TARGET_START = "2003-06-01"
TARGET_END = "2003-08-31"
BASELINE_START_YEAR = 1992
BASELINE_END_YEAR = 2002
FILE_PATH = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

ds = xr.open_dataset(FILE_PATH, engine="h5netcdf")

# The coordinates are latitude and longitude
ds_subset = ds.sel(
    latitude=slice(LAT_MIN, LAT_MAX),
    longitude=slice(LON_MIN, LON_MAX),
    time=slice("1991-12-27", "2003-08-31")
).load()

sst = ds_subset.sst.astype(np.float64)
lat = ds_subset.latitude.values
lon = ds_subset.longitude.values
time = pd.to_datetime(ds_subset.time.values)

target_mask = (time >= pd.Timestamp(TARGET_START)) & (time <= pd.Timestamp(TARGET_END))
target_times = time[target_mask]
target_sst = sst.sel(time=slice(TARGET_START, TARGET_END))

finite_mask = np.isfinite(target_sst.values)
sea_cells_mask = np.all(finite_mask, axis=0)
sea_lat_idx, sea_lon_idx = np.where(sea_cells_mask)
num_sea_cells = len(sea_lat_idx)

baseline_years = range(BASELINE_START_YEAR, BASELINE_END_YEAR + 1)
doy_range = [d for d in range(1, 367) if d != 60]

windows = {}
for d in doy_range:
    win_list = []
    for y in baseline_years:
        b_date = get_date_from_doy(y, d)
        if b_date:
            win_list.append((b_date - pd.Timedelta(days=5), b_date + pd.Timedelta(days=5)))
    windows[d] = win_list

baseline_sst = sst.sel(time=slice("1991-12-27", "2003-01-05"))
baseline_times = pd.to_datetime(baseline_sst.time.values)

thresholds = np.full((len(lat), len(lon), 366), np.nan, dtype=np.float64)
climatologies = np.full((len(lat), len(lon), 366), np.nan, dtype=np.float64)

# Pre-calculate the window masks for each doy to speed up
doy_masks = {}
for d in doy_range:
    mask = np.zeros(len(baseline_times), dtype=bool)
    for start_win, end_win in windows[d]:
        mask |= (baseline_times >= start_win) & (baseline_times <= end_win)
    doy_masks[d] = mask

for i in range(num_sea_cells):
    slat, slon = sea_lat_idx[i], sea_lon_idx[i]
    cell_sst_baseline = baseline_sst.isel(latitude=slat, longitude=slon).values
    
    for d in doy_range:
        pool = cell_sst_baseline[doy_masks[d]]
        pool = pool[np.isfinite(pool)]
        if len(pool) > 0:
            thresholds[slat, slon, d-1] = np.nanpercentile(pool, 90, method='hazen')
            climatologies[slat, slon, d-1] = np.nanmean(pool)

thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatologies[:, :, 59] = (climatologies[:, :, 58] + climatologies[:, :, 60]) / 2

def smooth_array(arr):
    smoothed = np.full_like(arr)
    for i in range(366):
        indices = [(i + k) % 366 for k in range(-15, 16)]
        smoothed[:, :, i] = np.nanmean(arr[:, :, indices], axis=-1)
    return smoothed

smoothed_thresholds = smooth_array(thresholds)

target_sst_vals = target_sst.values
target_doy = np.array([get_doy(t) for t in target_times])

mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)

for i in range(num_sea_cells):
    slat, slon = sea_lat_idx[i], sea_lon_idx[i]
    cell_sst_target = target_sst_vals[:, slat, slon]
    cell_thresh_target = smoothed_thresholds[slat, slon, target_doy - 1]
    
    is_hot = cell_sst_target >= cell_thresh_target
    
    runs = []
    start = None
    for t in range(len(is_hot)):
        if is_hot[t] and start is None:
            start = t
        elif not is_hot[t] and start is not None:
            runs.append([start, t - 1])
            start = None
    if start is not None:
        runs.append([start, len(is_hot) - 1])
        
    mhw_runs = [run for run in runs if run[1] - run[0] + 1 >= 5]
    
    if not mhw_runs:
        continue
        
    mhw_runs.sort()
    joined = False
    while not joined:
        joined = True
        new_runs = []
        if not mhw_runs: break
        curr_start, curr_end = mhw_runs[0]
        for next_start, next_end in mhw_runs[1:]:
            gap = next_start - curr_end - 1
            if gap <= 2:
                curr_end = next_end
                joined = False
            else:
                new_runs.append([curr_start, curr_end])
                curr_start, curr_end = next_start, next_end
        new_runs.append([curr_start, curr_end])
        mhw_runs = new_runs
        if joined: break
    
    for start, end in mhw_runs:
        mhw_mask[start:end+1, slat, slon] = 1

active_days = np.zeros(len(target_times), dtype=bool)
for t in range(len(target_times)):
    active_days[t] = np.any(mhw_mask[t] & sea_cells_mask)

regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t] and start is None:
        start = t
    elif not active_days[t] and start is not None:
        regional_events.append({
            "onset": target_times[start].strftime('%Y-%m-%d'),
            "end": target_times[t-1].strftime('%Y-%m-%d')
        })
        start = None
if start is not None:
    regional_events.append({
        "onset": target_times[start].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    })

out_ds = xr.Dataset(
    {"mhw": (["time", "latitude", "longitude"], mhw_mask.astype(np.uint8))},
    coords={"time": target_times, "latitude": lat, "longitude": lon}
)
out_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Success")
