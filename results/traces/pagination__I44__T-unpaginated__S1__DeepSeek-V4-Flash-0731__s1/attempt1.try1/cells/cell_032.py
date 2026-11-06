import os

# Check output files exist
print("Checking output files:")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    exists = os.path.exists(f)
    size = os.path.getsize(f) if exists else 0
    print(f"  {f}: exists={exists}, size={size}")

# Read back and verify the NetCDF file
import xarray as xr
import numpy as np
import json

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nNetCDF dimensions: {dict(ds.sizes)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw values: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {ds['mhw'].values.sum()}")
print(f"time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
ds.close()

# Read back and verify the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport fields: {list(report.keys())}")
print(f"Report events: {report['events']}")
print(f"Report complete: {report['complete']}")
print(f"Report caveats: '{report['caveats']}'")
