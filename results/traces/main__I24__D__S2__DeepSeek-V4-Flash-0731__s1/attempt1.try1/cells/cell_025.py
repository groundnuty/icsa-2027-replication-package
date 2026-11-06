
import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# Load the dataset to get coordinate values
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

# Get region coordinates from dataset
region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
region_lats = region.latitude.values
region_lons = region.longitude.values

# Target times
target_sel = region.sel(time=slice('2004-06-01', '2004-08-31'))
target_times = target_sel.time.values

# Load MHW mask
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60)

# Verify shape
assert mhw_mask.shape == (len(target_times), len(region_lats), len(region_lons)), \
    f"Shape mismatch: {mhw_mask.shape} vs {(len(target_times), len(region_lats), len(region_lons))}"

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray dataset for MHW mask
mhw_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask.astype(np.uint8))
    },
    coords={
        'time': target_times,
        'lat': region_lats,
        'lon': region_lons,
    }
)

# Write NetCDF
mhw_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write report.json
# Regional events
mhw_2d = mhw_mask.sum(axis=(1, 2)) > 0  # active days
active_indices = np.where(mhw_2d)[0]
events = []
if len(active_indices) > 0:
    start = active_indices[0]
    prev = start
    for idx in active_indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            events.append((start, prev))
            start = idx
            prev = idx
    events.append((start, prev))

tt = pd.to_datetime(target_times)
event_list = []
for s, e in events:
    event_list.append({
        "onset": tt[s].strftime('%Y-%m-%d'),
        "end": tt[e].strftime('%Y-%m-%d')
    })

# Baseline analysed: first and last baseline day used
# The baseline period is [1991-12-27, 2003-01-05]
baseline_start = "1991-12-27"
baseline_end = "2003-01-05"

# Target analysed
target_start = "2004-06-01"
target_end = "2004-08-31"

report = {
    "region": {
        "lat_min": lat_min,
        "lat_max": lat_max,
        "lon_min": lon_min,
        "lon_max": lon_max
    },
    "baseline_analysed": {
        "start": baseline_start,
        "end": baseline_end
    },
    "target_analysed": {
        "start": target_start,
        "end": target_end
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote output/report.json")
print("Report:", json.dumps(report, indent=2))
