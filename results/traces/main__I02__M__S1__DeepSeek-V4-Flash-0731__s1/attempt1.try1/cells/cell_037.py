
import numpy as np
import xarray as xr
import json
import os
from datetime import date, timedelta
import pickle

# Create output directory
os.makedirs('output', exist_ok=True)

# Load target dates
with open('/tmp/dates.pkl', 'rb') as f:
    dates = pickle.load(f)
target_dates = dates['target_dates']

# Load cell_mhw (per-cell MHW mask)
cell_mhw = np.load('/tmp/cell_mhw.npy')  # shape (60, 60, 92)
# But the output needs (time, lat, lon), so transpose
# cell_mhw has shape (lat, lon, time), we need (time, lat, lon)
mhw_values = cell_mhw.transpose(2, 0, 1)  # shape (92, 60, 60)
print(f"mhw_values shape: {mhw_values.shape}")

# Get coordinate values from the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc', engine='h5netcdf')
lat_vals = ds.latitude.values[34:94]
lon_vals = ds.longitude.values[213:273]
time_vals = np.array([np.datetime64(d) for d in target_dates])
ds.close()

print(f"time_vals shape: {time_vals.shape}")
print(f"First few time values: {time_vals[:5]}")

# Create the mhw_mask.nc file
mhw_uint8 = mhw_values.astype(np.uint8)
print(f"mhw_uint8 dtype: {mhw_uint8.dtype}")
print(f"mhw_uint8 unique values: {np.unique(mhw_uint8)}")

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': time_vals,
        'lat': lat_vals,
        'lon': lon_vals
    }
)

# Write the NetCDF file
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc written successfully")

# Create report.json
report = {
    "region": {
        "lat_min": 54.17,
        "lat_max": 55.37,
        "lon_min": 13.25,
        "lon_max": 14.45
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2004-06-01",
        "end": "2004-08-31"
    },
    "events": [],
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("report.json written successfully")

# Verify the output files
print("\nVerifying output:")
print(f"mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.exists('output/report.json')}")

# Verify report.json content
with open('output/report.json', 'r') as f:
    report_check = json.load(f)
print(f"report.json fields: {list(report_check.keys())}")
print(f"report.json events: {report_check['events']}")
print(f"report.json complete: {report_check['complete']}")
