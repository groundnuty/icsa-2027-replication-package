
import numpy as np
import pandas as pd
import xarray as xr
import json
import os

# Reload corrected MHW mask
mhw_mask = np.load('/work/mhw_mask_corrected.npy')

# Active days: at least one sea cell in an MHW
active = mhw_mask.any(axis=(0, 1))
print("Active days:", active.sum())
print("Active pattern:", active.astype(int))

# Find regional events (maximal runs of consecutive active days)
runs = []
t = 0
n_time = len(active)
while t < n_time:
    if active[t]:
        start = t
        while t < n_time and active[t]:
            t += 1
        end = t - 1
        runs.append((start, end))
    else:
        t += 1

print("Regional events (start_idx, end_idx):", runs)

# Get dates
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_dates = pd.to_datetime(target.time.values).date

events = []
for start, end in runs:
    onset = str(target_dates[start])
    end_date = str(target_dates[end])
    events.append({'onset': onset, 'end': end_date})
    print(f"Event: {onset} to {end_date}")

# Write mhw_mask.nc
os.makedirs('output', exist_ok=True)

mhw_transposed = mhw_mask.transpose(2, 0, 1).astype(np.uint8)  # (n_time, 60, 60)

lat = region.latitude.values
lon = region.longitude.values
time_vals = target.time.values

out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_transposed)
    },
    coords={
        'time': time_vals,
        'lat': lat,
        'lon': lon
    }
)
out_ds.mhw.attrs['units'] = '1'
out_ds.mhw.attrs['long_name'] = 'marine heatwave mask (1=inside per-cell MHW)'

out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("\nWritten mhw_mask.nc")

# Write report.json
report = {
    'region': {
        'lat_min': 55.67,
        'lat_max': 56.87,
        'lon_min': 16.45,
        'lon_max': 17.65
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05'
    },
    'target_analysed': {
        'start': '2021-06-01',
        'end': '2021-08-31'
    },
    'events': events,
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Written report.json")
print(json.dumps(report, indent=2))
