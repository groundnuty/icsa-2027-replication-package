
import xarray as xr
import numpy as np
import json

# Read back the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc')
print("NetCDF contents:")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw dims: {ds['mhw'].dims}")
print(f"\nmhw min/max: {ds['mhw'].min().item()}, {ds['mhw'].max().item()}")
print(f"Sum of mhw: {ds['mhw'].sum().item()}")
print(f"\ntime values:")
print(ds['time'].values[:3], "...", ds['time'].values[-3:])
print(f"\nlat values: {ds['lat'].values[:3]} ... {ds['lat'].values[-3:]}")
print(f"lon values: {ds['lon'].values[:3]} ... {ds['lon'].values[-3:]}")

# Read back the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport JSON:")
print(json.dumps(report, indent=2))
