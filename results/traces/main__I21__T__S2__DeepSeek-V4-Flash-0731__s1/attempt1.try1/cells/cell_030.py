
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("mhw_mask.nc:")
print(ds)
print(f"\nVariable dtype: {ds['mhw'].dtype}")
print(f"Shape: {ds['mhw'].shape}")
print(f"Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"Unique values in mhw: {np.unique(ds['mhw'].values)}")
print(f"Number of 1s: {np.sum(ds['mhw'].values == 1)}")
print(f"Number of 0s: {np.sum(ds['mhw'].values == 0)}")
print(f"Total: {ds['mhw'].values.size}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(json.dumps(report, indent=2))
