import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Region and period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = pd.Timestamp('2012-06-01')
target_end = pd.Timestamp('2012-08-31')
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

def get_doy(dt):
    return dt.day_of_year

def load_sst_region(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords = None
    
    for date in dates:
        filename = f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        with fs.open(filename, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            subset = ds.analysed_sst.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            ).squeeze()
            if coords is None:
                coords = {
                    'latitude': subset.latitude.values,
                    'longitude': subset.longitude.values,
                    'time': dates
                }
            sst_list.append(subset.values)
    
    return np.array(sst_list, dtype='float64'), coords

# Target data
target_sst, target_coords = load_sst_region(target_start, target_end)
t_lat = target_coords['latitude']
t_lon = target_coords['longitude']
t_time = target_coords['time']

# Baseline data
baseline_load_start = baseline_start - pd.Timedelta(days=5)
baseline_load_end = baseline_end + pd.Timedelta(days=5)
baseline_sst, baseline_coords = load_sst_region(baseline_load_start, baseline_load_end)
b_time = baseline_coords['time']

date_to_idx = {date: i for i, date in enumerate(b_time)}
baseline_dates = pd.date_range(baseline_start, baseline_end)

lat_len = len(t_lat)
lon_len = len(t_lon)
thresholds = np.full((366, lat_len, lon_len), np.nan, dtype='float64')
climatology = np.full((366, lat_len, lon_len), np.nan, dtype='float64')

for d in range(1, 367):
    if d == 60:
        continue
    
    matching_baseline_dates = [date for date in baseline_dates if date.day_of_year == d]
    
    pool_indices = set()
    for b_date in matching_baseline_dates:
        for offset in range(-5, 6):
            check_date = b_date + pd.Timedelta(days=offset)
            if check_date in date_to_idx:
                pool_indices.add(date_to_idx[check_date])
    
    if pool_indices:
        pool_data = baseline_sst[list(pool_indices)]
        thresholds[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_wrap(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
        window_data = arr[window_indices]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_wrap(thresholds)
climatology = smooth_wrap(climatology)

mhw_mask = np.zeros(target_sst.shape, dtype='uint8')

for i in range(lat_len):
    for j in range(lon_len):
        cell_sst = target_sst[:, i, j]
        if not np.all(np.isfinite(cell_sst)):
            continue
        
        doys = np.array([get_doy(t) for t in t_time])
        cell_thresholds = thresholds[doys - 1, i, j]
        hot = cell_sst >= cell_thresholds
        
        in_mhw = np.zeros(len(hot), dtype=bool)
        count = 0
        start_idx = 0
        for k in range(len(hot)):
            if hot[k]:
                if count == 0: start_idx = k
                count += 1
            else:
                if count >= 5:
                    in_mhw[start_idx : start_idx + count] = True
                count = 0
        if count >= 5:
            in_mhw[start_idx : start_idx + count] = True
            
        while True:
            changed = False
            for k in range(1, len(in_mhw) - 1):
                if not in_mhw[k] and in_mhw[k-1] and in_mhw[k+1]:
                    in_mhw[k] = True
                    changed = True
            for k in range(1, len(in_mhw) - 2):
                if not in_mhw[k] and not in_mhw[k+1] and in_mhw[k-1] and in_mhw[k+2]:
                    in_mhw[k] = True
                    in_mhw[k+1] = True
                    changed = True
            if not changed:
                break
        
        mhw_mask[:, i, j] = in_mhw.astype('uint8')

active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
in_event = False
onset = None
for k in range(len(active_days)):
    if active_days[k] and not in_event:
        in_event = True
        onset = t_time[k]
    elif not active_days[k] and in_event:
        in_event = False
        regional_events.append({"onset": onset.strftime('%Y-%m-%d'), "end": t_time[k-1].strftime('%Y-%m-%d')})
if in_event:
    regional_events.append({"onset": onset.strftime('%Y-%m-%d'), "end": t_time[-1].strftime('%Y-%m-%d')})

# Create output dir
os.makedirs("output", exist_ok=True)

ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": t_time, "lat": t_lat, "lon": t_lon}
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
