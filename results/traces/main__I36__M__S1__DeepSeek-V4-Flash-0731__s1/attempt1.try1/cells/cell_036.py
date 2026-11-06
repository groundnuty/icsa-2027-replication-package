
import os

# Check current directory
print(f"Current working directory: {os.getcwd()}")
print(f"Contents: {os.listdir('.')}")
print(f"Output dir contents: {os.listdir('output') if os.path.exists('output') else 'MISSING'}")

# Check file sizes
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        print(f"{f}: {os.path.getsize(f)} bytes")
    else:
        print(f"{f}: MISSING")

# Verify the files can be read
import xarray as xr
import json

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nVerified mhw_mask.nc:")
print(f"  Variables: {list(ds.data_vars)}")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
ds.close()

with open('output/report.json') as f:
    report = json.load(f)
print(f"\nVerified report.json:")
print(f"  Fields: {list(report.keys())}")
print(f"  events: {report['events']}")
