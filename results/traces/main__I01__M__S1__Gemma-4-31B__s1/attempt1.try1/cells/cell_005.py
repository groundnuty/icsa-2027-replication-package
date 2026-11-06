import os
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# Region and periods
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87
baseline_start = pd.to_datetime("1992-01-01")
baseline_end = pd.to_datetime("2002-12-31")
target_start = pd.to_datetime("2008-06-01")
target_end = pd.to_datetime("2008-08-31")

dataset_dir = "/data/icsa2027_data_20261101T090944Z/s1z"

def get_custom_doy(dt):
    """
    Map date to doy 1-366:
    1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    """
    # Using a fixed leap year (e.g., 2000) to get the mapping for any month/day
    # datetime(2000, month, day).timetuple().tm_yday
    return datetime(2000, dt.month, dt.day).timetuple().tm_yday

def get_date_from_filename(filename):
    date_str = filename.split('_')[1].split('.')[0]
    return pd.to_datetime(date_str, format='%Y%m%d')

all_files = os.listdir(dataset_dir)
baseline_files = sorted([f for f in all_files if f.startswith('sst_') and f.endswith('.nc') and 
                         (baseline_start - pd.Timedelta(days=5)) <= get_date_from_filename(f) <= (baseline_end + pd.Timedelta(days=5))])
target_files = sorted([f for f in all_files if f.startswith('sst_') and f.endswith('.nc') and 
                       target_start <= get_date_from_filename(f) <= target_end])

def load_sst_precise(files):
    data = []
    times = []
    lat_coords = None
    lon_coords = None
    for f in files:
        path = os.path.join(dataset_dir, f)
        with xr.open_dataset(path, engine="h5netcdf") as ds:
            subset = ds.analysed_sst.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
            data.append(subset.values.squeeze())
            times.append(ds.time.values[0])
            if lat_coords is None:
                lat_coords = subset.latitude.values
                lon_coords = subset.longitude.values
    return np.array(data, dtype=np.float64), np.array(times), lat_coords, lon_coords

sst_baseline, times_baseline, lats, lons = load_sst_precise(baseline_files)
sst_target, times_target, _, _ = load_sst_precise(target_files)

# 1. Sea cells: finite SST on every day of target period
sea_mask = np.all(np.isfinite(sst_target), axis=0)
n_lat, n_lon = sst_target.shape[1:]

# 2. Threshold and Climatology
# Use custom doy
doy_baseline = np.array([get_custom_doy(pd.to_datetime(t)) for t in times_baseline])

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

date_to_idx = {pd.to_datetime(t): i for i, t in enumerate(times_baseline)}
all_baseline_dates = sorted(date_to_idx.keys())

# Pre-calculate which dates fall into which doy for baseline
doy_to_dates = {}
for date in all_baseline_dates:
    d = get_custom_doy(date)
    if d not in doy_to_dates:
        doy_to_dates[d] = []
    doy_to_dates[d].append(date)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool = []
    # Baseline dates with custom doy == d
    dates_with_d = doy_to_dates.get(d, [])
    for date in dates_with_d:
        # Window [date-5, date+5]
        for offset in range(-5, 6):
            win_date = date + pd.Timedelta(days=offset)
            if win_date in date_to_idx:
                pool.append(sst_baseline[date_to_idx[win_date]])
    
    if pool:
        pool_arr = np.array(pool)
        thresholds[d-1] = np.nanpercentile(pool_arr, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_arr, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
hot_days = np.zeros((len(times_target), n_lat, n_lon), dtype=bool)
for i, t in enumerate(times_target):
    doy = get_custom_doy(pd.to_datetime(t))
    hot_days[i] = (sst_target[i] >= thresholds[doy-1])

mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)
for lat_idx in range(n_lat):
    for lon_idx in range(n_lon):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        cell_hot = hot_days[:, lat_idx, lon_idx]
        is_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        i = 0
        while i < len(cell_hot):
            if cell_hot[i]:
                start = i
                while i < len(cell_hot) and cell_hot[i]:
                    i += 1
                end = i
                if (end - start) >= 5:
                    is_mhw[start:end] = True
            else:
                i += 1
        
        changed = True
        while changed:
            changed = False
            for i in range(len(is_mhw) - 2):
                if is_mhw[i]:
                    if i + 2 < len(is_mhw) and not is_mhw[i+1] and is_mhw[i+2]:
                        is_mhw[i+1] = True
                        changed = True
                    elif i + 3 < len(is_mhw) and not is_mhw[i+1] and not is_mhw[i+2] and is_mhw[i+3]:
                        is_mhw[i+1] = True
                        is_mhw[i+2] = True
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
        end = i - 1
        regional_events.append({
            "onset": pd.to_datetime(times_target[start]).strftime('%Y-%m-%d'),
            "end": pd.to_datetime(times_target[end]).strftime('%Y-%m-%d')
        })
    else:
        i += 1

os.makedirs("output", exist_ok=True)
ds_mask = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={"time": times_target, "latitude": lats, "longitude": lons}
)
ds_mask.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": pd.to_datetime(times_baseline[0]).strftime('%Y-%m-%d'),
        "end": pd.to_datetime(times_baseline[-1]).strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": pd.to_datetime(times_target[0]).strftime('%Y-%m-%d'),
        "end": pd.to_datetime(times_target[-1]).strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Analysis complete.")
