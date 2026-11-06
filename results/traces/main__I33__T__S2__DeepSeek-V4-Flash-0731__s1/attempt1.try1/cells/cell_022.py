
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict
import json
import os

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')

print("thresholds_smooth shape:", thresholds_smooth.shape)
print("climatology_smooth shape:", climatology_smooth.shape)

# Check for NaN in sea cells
target_sst = target_data.analysed_sst.values
n_days, n_lat, n_lon = target_sst.shape

# Sea cells
sea_mask = np.all(~np.isnan(target_sst), axis=0)
print("Sea cells:", np.sum(sea_mask))

# Check if any sea cell has NaN threshold/climatology
for doy in range(1, 367):
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j]:
                if np.isnan(thresholds_smooth[doy, i, j]):
                    print(f"NaN threshold at doy={doy}, cell=({i},{j})")
                    break
                if np.isnan(climatology_smooth[doy, i, j]):
                    print(f"NaN climatology at doy={doy}, cell=({i},{j})")
                    break
        else:
            continue
        break
else:
    print("No NaN in thresholds/climatology for sea cells")

# Target data
target_time = target_data.time.values
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

# Hot days
threshold_for_target = np.array([thresholds_smooth[doy] for doy in target_doys])
hot = (target_sst >= threshold_for_target) & sea_mask[np.newaxis, :, :]

# Per-cell MHW detection
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        hot_cell = hot[:, i, j]
        
        # Find runs of consecutive hot days
        runs = []
        in_run = False
        run_start = 0
        for d in range(n_days):
            if hot_cell[d]:
                if not in_run:
                    run_start = d
                    in_run = True
            else:
                if in_run:
                    runs.append((run_start, d - 1))
                    in_run = False
        if in_run:
            runs.append((run_start, n_days - 1))
        
        # Keep only runs of >= 5 days
        runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        # Join runs separated by 1 or 2 non-hot days
        if len(runs) > 0:
            joined_runs = [list(runs[0])]
            for k in range(1, len(runs)):
                gap = runs[k][0] - joined_runs[-1][1] - 1
                if gap <= 2:
                    joined_runs[-1][1] = runs[k][1]
                else:
                    joined_runs.append(list(runs[k]))
            
            for start, end in joined_runs:
                mhw_mask[start:end+1, i, j] = 1

# Regional events
active = mhw_mask.sum(axis=(1, 2)) > 0
events = []
in_event = False
event_start = 0
for d in range(n_days):
    if active[d]:
        if not in_event:
            event_start = d
            in_event = True
    else:
        if in_event:
            events.append((event_start, d - 1))
            in_event = False
if in_event:
    events.append((event_start, n_days - 1))

print("Regional events:")
event_list = []
for start, end in events:
    onset = target_dates[start].isoformat()
    end_date = target_dates[end].isoformat()
    event_list.append({"onset": onset, "end": end_date})
    print(f"  {onset} to {end_date}")

# Create output directory
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
# Need to use the region's grid cells and target days with the dataset's coordinate values
lat_vals = target_data.latitude.values
lon_vals = target_data.longitude.values
time_vals = target_data.time.values

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_vals,
        'lat': lat_vals,
        'lon': lon_vals,
    }
)
ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave mask (1=inside per-cell MHW)'

ds_out.to_netcdf('output/mhw_mask.nc')
print("Written output/mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": 59.05,
        "lat_max": 60.25,
        "lon_min": 21.25,
        "lon_max": 22.45
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2014-06-01",
        "end": "2014-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Written output/report.json")
