import os
os.makedirs('output', exist_ok=True)

import numpy as np
import pickle
import json
import xarray as xr
from datetime import date, timedelta
import fsspec

# Reload all needed data
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')
sea_cells = np.load('/tmp/work/sea_cells.npy')
with open('/tmp/work/target_dates.pkl', 'rb') as f:
    target_dates = pickle.load(f)
with open('/tmp/work/events.pkl', 'rb') as f:
    events = pickle.load(f)
region_lat = np.load('/tmp/work/region_lat.npy')
region_lon = np.load('/tmp/work/region_lon.npy')

# Print loaded data summary
print(f"per_cell_mhw: {per_cell_mhw.shape}, dtype={per_cell_mhw.dtype}")
print(f"sea_cells: {sea_cells.shape}")
print(f"target_dates: {len(target_dates)} days")
print(f"events: {events}")
print(f"region_lat: {region_lat.shape}, {region_lat[0]} to {region_lat[-1]}")
print(f"region_lon: {region_lon.shape}, {region_lon[0]} to {region_lon[-1]}")

# Create the mhw mask as uint8
mhw_uint8 = per_cell_mhw.astype(np.uint8)

# Create the time coordinates
time_vals = np.array(target_dates, dtype='datetime64[ns]')

# Create the output NetCDF file
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': time_vals,
        'lat': region_lat,
        'lon': region_lon
    }
)

# Set attributes
ds_out['mhw'].attrs['long_name'] = 'marine heatwave mask'
ds_out['mhw'].attrs['description'] = '1 if the cell is inside a per-cell MHW on that day, 0 otherwise'
ds_out['mhw'].attrs['units'] = '1'
ds_out['lat'].attrs['units'] = 'degrees_north'
ds_out['lat'].attrs['standard_name'] = 'latitude'
ds_out['lon'].attrs['units'] = 'degrees_east'
ds_out['lon'].attrs['standard_name'] = 'longitude'
ds_out['time'].attrs['standard_name'] = 'time'

# Save the NetCDF file
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Saved output/mhw_mask.nc")

# Create the report
report = {
    "region": {
        "lat_min": 63.31,
        "lat_max": 64.51,
        "lon_min": 21.31,
        "lon_max": 22.51
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2004-06-01",
        "end": "2004-08-31"
    },
    "events": [
        {"onset": str(target_dates[s]), "end": str(target_dates[e])}
        for s, e in events
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Saved output/report.json")
print(json.dumps(report, indent=2))
