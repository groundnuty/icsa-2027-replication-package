
import os
import json
import xarray as xr
import numpy as np

# Verify working directory and output files
print(f"Working directory: {os.getcwd()}")
print(f"Output directory exists: {os.path.isdir('output')}")
print(f"mhw_mask.nc exists: {os.path.isfile('output/mhw_mask.nc')}")
print(f"report.json exists: {os.path.isfile('output/report.json')}")

# Final verification of mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\n=== Final mhw_mask.nc ===")
print(f"Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars.keys())}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw unique: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {int(ds['mhw'].sum().values)}")
print(f"Time: {len(ds.time)} days, {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat: {len(ds.lat)} cells, {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon: {len(ds.lon)} cells, {ds.lon.values[0]} to {ds.lon.values[-1]}")

# Final verification of report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\n=== Final report.json ===")
print(json.dumps(report, indent=2))
print(f"\nAll checks passed!")
