
import numpy as np
import xarray as xr
import json
import pandas as pd

# Load intermediate results
mhw_cell = np.load('/tmp/mhw_cell.npy')  # (92, 60, 60) boolean
sea_cells = np.load('/tmp/sea_cells.npy')
target_dates = np.load('/tmp/target_dates.npy')
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')

print("mhw_cell shape:", mhw_cell.shape)
print("mhw_cell dtype:", mhw_cell.dtype)
print("Target dates count:", len(target_dates))

# Convert boolean to uint8 (1 for in-MHW, 0 for not)
mhw_mask = mhw_cell.astype(np.uint8)

# Verify
print("mhw_mask dtype:", mhw_mask.dtype)
print("mhw_mask sum:", mhw_mask.sum())
print("Unique values:", np.unique(mhw_mask))

# Create the NetCDF output
# Coordinates from dataset
time_coords = target_dates  # already from dataset
lat_coords = region_lat
lon_coords = region_lon

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)

# Set attributes
ds_out['mhw'].attrs['description'] = 'Marine heatwave mask: 1 if cell is inside a per-cell MHW on that day, 0 otherwise'
ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['long_name'] = 'marine_heatwave_mask'

# Save
import os
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved mhw_mask.nc")

# Prepare report.json
report = {
    "region": {
        "lat_min": 54.45,
        "lat_max": 55.65,
        "lon_min": 16.05,
        "lon_max": 17.25
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2012-06-01",
        "end": "2012-08-31"
    },
    "events": [
        {"onset": "2012-06-11", "end": "2012-06-16"},
        {"onset": "2012-07-25", "end": "2012-07-29"}
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Saved report.json")
print(json.dumps(report, indent=2))
