import numpy as np
import xarray as xr
import fsspec
import json
from datetime import datetime, timedelta

# Reload and check
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Verify the output files
import os
print("Output files:")
for root, dirs, files in os.walk('output'):
    for file in files:
        path = os.path.join(root, file)
        print(f"  {path}: {os.path.getsize(path)} bytes")

# Verify report.json
with open('output/report.json', 'r') as fjson:
    report = json.load(fjson)
print("\nReport:")
print(json.dumps(report, indent=2))

# Verify mhw_mask.nc
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nmhw_mask.nc:")
print(ds_out)
print(f"mhw dtype: {ds_out['mhw'].dtype}")
print(f"mhw shape: {ds_out['mhw'].shape}")
print(f"mhw values: {np.unique(ds_out['mhw'].values)}")
print(f"mhw sum: {ds_out['mhw'].values.sum()}")
print(f"Time coords: {ds_out['time'].values[:5]}...{ds_out['time'].values[-5:]}")
print(f"Lat coords: {ds_out['lat'].values[:3]}...{ds_out['lat'].values[-3:]}")
print(f"Lon coords: {ds_out['lon'].values[:3]}...{ds_out['lon'].values[-3:]}")
