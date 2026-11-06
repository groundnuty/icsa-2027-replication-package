
import os
import json
import xarray as xr
import numpy as np

# Verify output files exist
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.exists('output/report.json'))

# Check file sizes
print("mhw_mask.nc size:", os.path.getsize('output/mhw_mask.nc'), "bytes")
print("report.json size:", os.path.getsize('output/report.json'), "bytes")

# Verify NetCDF content
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nNetCDF structure:")
print(ds)
print("mhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw values: 0 count =", (ds.mhw.values == 0).sum(), ", 1 count =", (ds.mhw.values == 1).sum())

# Verify report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport fields:", list(report.keys()))
print("Events:", report['events'])
print("Complete:", report['complete'])
