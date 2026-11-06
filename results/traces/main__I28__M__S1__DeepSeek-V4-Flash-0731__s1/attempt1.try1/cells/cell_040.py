
import os
import json
import xarray as xr
import numpy as np

# Check output files exist
print("Output files:")
print("  mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("  report.json exists:", os.path.exists('output/report.json'))
print("  File sizes:")
print(f"    mhw_mask.nc: {os.path.getsize('output/mhw_mask.nc')} bytes")
print(f"    report.json: {os.path.getsize('output/report.json')} bytes")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport content:")
print(json.dumps(report, indent=2))

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\nmhw_mask.nc:")
print(f"  Dimensions: {dict(ds.dims)}")
print(f"  Variable: {list(ds.data_vars)}")
print(f"  mhw dtype: {ds['mhw'].dtype}")
print(f"  mhw shape: {ds['mhw'].shape}")
print(f"  time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"  lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"  lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
print(f"  Sum of mhw: {np.sum(ds['mhw'].values)}")
print(f"  Unique values: {np.unique(ds['mhw'].values)}")
ds.close()

print("\nAll output files verified successfully.")
