
import os
import json
import xarray as xr
import numpy as np

# Check output files exist
print("Output files:")
for f in os.listdir('output'):
    path = os.path.join('output', f)
    size = os.path.getsize(path)
    print(f"  {f}: {size} bytes")

# Read back mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variables: {list(ds.variables)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  mhw values: min={ds.mhw.min().item()}, max={ds.mhw.max().item()}")
print(f"  mhw sum: {ds.mhw.sum().item()}")
print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat range: {ds.lat.values[0]:.4f} to {ds.lat.values[-1]:.4f}")
print(f"  Lon range: {ds.lon.values[0]:.4f} to {ds.lon.values[-1]:.4f}")
ds.close()

# Read back report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(json.dumps(report, indent=2))
