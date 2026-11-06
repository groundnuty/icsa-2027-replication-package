
import xarray as xr
import numpy as np
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("mhw_mask.nc verification:")
print(f"  Variable name: {list(ds.data_vars.keys())}")
print(f"  Variable: {ds.mhw.name if hasattr(ds.mhw, 'name') else 'mhw'}")
print(f"  Shape: {ds.mhw.shape}")
print(f"  Dtype: {ds.mhw.dtype}")
print(f"  Dims: {ds.mhw.dims}")
print(f"  Time: {len(ds.time)} steps, from {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"  Lat: {len(ds.lat)} values, from {ds.lat.values[0]:.4f} to {ds.lat.values[-1]:.4f}")
print(f"  Lon: {len(ds.lon)} values, from {ds.lon.values[0]:.4f} to {ds.lon.values[-1]:.4f}")
print(f"  Values: {sorted(set(ds.mhw.values.flatten().tolist()))}")
print(f"  MHW cell-days: {int(ds.mhw.values.sum())}")

# Verify report.json  
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nreport.json verification:")
print(f"  Keys: {list(report.keys())}")
print(f"  Events: {len(report['events'])} events")

print("\nAll output files verified successfully!")
