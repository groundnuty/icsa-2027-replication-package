
import numpy as np
import pandas as pd
import os
import json
import xarray as xr

# Load saved intermediate results
threshold_smoothed = np.load('output/threshold_smoothed.npy')
sea_mask = np.load('output/sea_mask.npy')
target_sst_sea = np.load('output/target_sst_sea.npy')
target_time = np.load('output/target_time.npy')
lat_values = np.load('output/lat_values.npy')
lon_values = np.load('output/lon_values.npy')
target_doy = np.load('output/target_doy.npy')

n_target = len(target_doy)
n_sea = target_sst_sea.shape[1]

# Compute hot matrix
hot = np.zeros((n_target, n_sea), dtype=bool)
target_sst_sea_f64 = target_sst_sea.astype(np.float64)
for i in range(n_target):
    doy = target_doy[i]
    hot[i, :] = target_sst_sea_f64[i, :] >= threshold_smoothed[doy-1, :]

def find_cell_mhws_v2(hot_series):
    n = len(hot_series)
    runs = []
    i = 0
    while i < n:
        if hot_series[i]:
            start = i
            while i < n and hot_series[i]:
                i += 1
            runs.append((start, i - 1))
        else:
            i += 1
    
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    if not mhws:
        return np.zeros(n, dtype=bool)
    
    joined_mhws = [list(mhws[0])]
    for mhw in mhws[1:]:
        gap = mhw[0] - joined_mhws[-1][1] - 1
        if 1 <= gap <= 2:
            joined_mhws[-1][1] = mhw[1]
        else:
            joined_mhws.append(list(mhw))
    
    inside_mhw = np.zeros(n, dtype=bool)
    for mhw in joined_mhws:
        inside_mhw[mhw[0]:mhw[1]+1] = True
    
    return inside_mhw

mhw_sea = np.zeros((n_target, n_sea), dtype=bool)
for c in range(n_sea):
    mhw_sea[:, c] = find_cell_mhws_v2(hot[:, c])

active = mhw_sea.sum(axis=1) > 0

# Find regional events
events = []
i = 0
while i < n_target:
    if active[i]:
        start = i
        while i < n_target and active[i]:
            i += 1
        events.append((start, i - 1))
    else:
        i += 1

# Build mhw_full for all grid cells
mhw_full = np.zeros((n_target, sea_mask.shape[0], sea_mask.shape[1]), dtype=np.uint8)
sea_indices = np.where(sea_mask)
for i in range(n_sea):
    lat_i, lon_i = sea_indices[0][i], sea_indices[1][i]
    mhw_full[:, lat_i, lon_i] = mhw_sea[:, i]

# =====================
# Write output/mhw_mask.nc
# =====================
os.makedirs('output', exist_ok=True)

# Create xarray Dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_full)
    },
    coords={
        'time': target_time,
        'lat': lat_values,
        'lon': lon_values,
    }
)

# Set mhw to uint8
ds_out['mhw'] = ds_out['mhw'].astype('uint8')

# Write to netCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# Verify the file
with xr.open_dataset('output/mhw_mask.nc') as ds_check:
    print(f"  Shape: {ds_check['mhw'].shape}")
    print(f"  Dtype: {ds_check['mhw'].dtype}")
    print(f"  Time range: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
    print(f"  Lat range: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}")
    print(f"  Lon range: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}")
    print(f"  Unique values: {np.unique(ds_check['mhw'].values)}")
    print(f"  Sum of mhw: {ds_check['mhw'].sum().values}")

# =====================
# Write output/report.json
# =====================

# Build events list
events_list = []
for onset_idx, end_idx in events:
    onset = pd.Timestamp(target_time[onset_idx]).strftime('%Y-%m-%d')
    end = pd.Timestamp(target_time[end_idx]).strftime('%Y-%m-%d')
    events_list.append({"onset": onset, "end": end})

report = {
    "region": {
        "lat_min": 57.57,
        "lat_max": 58.77,
        "lon_min": 10.25,
        "lon_max": 11.45
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2016-06-01",
        "end": "2016-08-31"
    },
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nWritten output/report.json")
print(json.dumps(report, indent=2))
