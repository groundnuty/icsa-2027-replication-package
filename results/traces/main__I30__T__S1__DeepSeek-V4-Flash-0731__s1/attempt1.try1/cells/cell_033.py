
import numpy as np
import pandas as pd
import json
import xarray as xr

# Load data
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')

print("mhw_mask shape:", mhw_mask.shape)
print("lat_vals:", lat_vals.shape, lat_vals[0], lat_vals[-1])
print("lon_vals:", lon_vals.shape, lon_vals[0], lon_vals[-1])
print("target_times:", target_times.shape, target_times[0], target_times[-1])

# Verify the mask
n_time, n_lat, n_lon = mhw_mask.shape
print("MHW mask value counts:", np.unique(mhw_mask, return_counts=True))

# Create the NetCDF output
# Use dataset coordinate values
time_coords = target_times
lat_coords = lat_vals
lon_coords = lon_vals

# mhw_mask is (time, lat, lon)
ds_out = xr.Dataset(
    {
        "mhw": (("time", "lat", "lon"), mhw_mask)
    },
    coords={
        "time": time_coords,
        "lat": lat_coords,
        "lon": lon_coords,
    }
)

# Set dtype
ds_out["mhw"] = ds_out["mhw"].astype("uint8")

# Create output directory
import os
os.makedirs('output', exist_ok=True)

# Write netCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")

# Report
report = {
    "region": {
        "lat_min": 58.69,
        "lat_max": 59.89,
        "lon_min": 18.69,
        "lon_max": 19.89
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2010-06-01",
        "end": "2010-08-31"
    },
    "events": [
        {"onset": "2010-06-27", "end": "2010-07-26"}
    ],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Written output/report.json")
print(json.dumps(report, indent=2))
