
import numpy as np
import pandas as pd
import xarray as xr
import json
import os

# Load all needed data
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_indices = np.load('/tmp/target_indices.npy')

# Target period info
n_lat = len(lat_vals)
n_lon = len(lon_vals)
n_target = len(target_indices)
print(f"Region: {n_lat} lat × {n_lon} lon, {n_target} target days")
print(f"Target days: {times[target_indices[0]].date()} to {times[target_indices[-1]].date()}")
print(f"Lat range: {lat_vals[0]} to {lat_vals[-1]}")
print(f"Lon range: {lon_vals[0]} to {lon_vals[-1]}")

# Build full 3D MHW mask (n_target, n_lat, n_lon)
mhw_full = np.zeros((n_target, n_lat, n_lon), dtype=np.uint8)

# Map per-cell MHW mask to full grid
for ci in range(len(sea_cells)):
    lat, lon = sea_cells[ci]
    mhw_full[:, lat, lon] = mhw_mask[ci, :]

print("MHW mask shape:", mhw_full.shape)
print("MHW cell-days:", mhw_full.sum())
print("Land cells:", mhw_full.shape[1] * mhw_full.shape[2] - len(sea_cells))

# Create output directory
os.makedirs('output', exist_ok=True)

# Create NetCDF file
# Coordinates
time_coords = times[target_indices].values  # datetime64[ns]
lat_coords = lat_vals  # float32
lon_coords = lon_vals  # float32

# Create dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_full)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)
ds_out['mhw'].attrs['description'] = 'Marine heatwave indicator: 1 if cell is inside a per-cell MHW, 0 otherwise'
ds_out['mhw'].attrs['units'] = '1'

# Set dtype to uint8
ds_out['mhw'] = ds_out['mhw'].astype('uint8')

# Save NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved output/mhw_mask.nc")

# Create report.json
# Regional events
active = (mhw_mask.sum(axis=0) > 0).astype(np.int8)
events = []
i = 0
while i < n_target:
    if active[i] == 1:
        j = i
        while j < n_target and active[j] == 1:
            j += 1
        events.append({
            "onset": str(times[target_indices[i]].date()),
            "end": str(times[target_indices[j-1]].date())
        })
        i = j
    else:
        i += 1

report = {
    "region": {
        "lat_min": 56.13,
        "lat_max": 57.33,
        "lon_min": 17.71,
        "lon_max": 18.91
    },
    "baseline_analysed": {
        "start": "1992-01-01",
        "end": "2002-12-31"
    },
    "target_analysed": {
        "start": "2015-06-01",
        "end": "2015-08-31"
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("\nReport:")
print(json.dumps(report, indent=2))
print("\nFiles written successfully.")
