import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Parameters
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
target_start = datetime(2005, 6, 1)
target_end = datetime(2005, 8, 31)
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_doy(date):
    y = date.year
    is_leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
    doy = date.timetuple().tm_yday
    if not is_leap and doy >= 60:
        doy += 1
    return doy

def load_sst_for_dates(dates):
    sst_list = []
    coords = None
    for date in dates:
        filename = os.path.join(data_dir, f"sst_{date.strftime('%Y%m%d')}.nc")
        with xr.open_dataset(filename, engine="h5netcdf") as ds:
            subset = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            if coords is None:
                coords = {'lat': subset.latitude.values, 'lon': subset.longitude.values}
            sst_list.append(subset.squeeze().values)
    return np.array(sst_list, dtype=np.float64), coords

# 1. Identify and Load Data
full_baseline_start = datetime(1991, 12, 27)
full_baseline_end = datetime(2003, 1, 5)

baseline_dates = pd.date_range(full_baseline_start, full_baseline_end)
target_dates = pd.date_range(target_start, target_end)

print("Loading baseline data...")
baseline_sst, coords = load_sst_for_dates(baseline_dates)

print("Loading target data...")
target_sst, _ = load_sst_for_dates(target_dates)

# 2. Sea cells
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells = is_finite

# 3. Threshold and climatology
nlat, nlon = baseline_sst.shape[1:]
thresholds = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

date_to_idx = {date: i for i, date in enumerate(baseline_dates)}
std_baseline_dates = pd.date_range(baseline_start, baseline_end)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_indices = []
    for bd in std_baseline_dates:
        if get_doy(bd) == d:
            for offset in range(-5, 6):
                win_date = bd + timedelta(days=offset)
                if win_date in date_to_idx:
                    pool_indices.append(date_to_idx[win_date])
    
    if not pool_indices:
        continue
        
    pool_data = baseline_sst[pool_indices, :, :]
    thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
    climatology[d-1] = np.nanmean(pool_data, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        window = []
        for i in range(-15, 16):
            idx = (d + i) % 366
            window.append(arr[idx])
        smoothed[d] = np.nanmean(np.stack(window), axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatology = smooth(climatology)

# 4. Per-cell MHWs
target_doy = np.array([get_doy(date) for date in target_dates])
threshold_target = np.stack([thresholds[d-1] for d in target_doy])

hot = target_sst >= threshold_target
hot = hot & sea_cells[np.newaxis, :, :]

mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(nlat):
    for j in range(nlon):
        if not sea_cells[i, j]:
            continue
            
        cell_hot = hot[:, i, j]
        in_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        runs = []
        start = None
        for k in range(len(cell_hot)):
            if cell_hot[k]:
                if start is None:
                    start = k
            else:
                if start is not None:
                    if k - start >= 5:
                        runs.append((start, k - 1))
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot) - 1))
        
        if not runs:
            continue
            
        merged_runs = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end <= 3: 
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
            
        for start, end in merged_runs:
            in_mhw[start : end + 1] = True
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# 5. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for k in range(len(active_days)):
    if active_days[k]:
        if start is None:
            start = k
    else:
        if start is not None:
            regional_events.append((target_dates[start].strftime('%Y-%m-%d'), target_dates[k-1].strftime('%Y-%m-%d')))
            start = None
if start is not None:
    regional_events.append((target_dates[start].strftime('%Y-%m-%d'), target_dates[-1].strftime('%Y-%m-%d')))

os.makedirs('output', exist_ok=True)

mhw_ds = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": target_dates, "lat": coords['lat'], "lon": coords['lon']}
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0], "end": e[1]} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
