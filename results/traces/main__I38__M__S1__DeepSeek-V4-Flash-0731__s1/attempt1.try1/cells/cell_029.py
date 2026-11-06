
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  Dimensions: {dict(ds.dims)}")
print(f"  Variable: {list(ds.data_vars)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw shape: {ds.mhw.shape}")
print(f"  time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  mhw sum: {ds.mhw.sum().values}")
print(f"  mhw max: {ds.mhw.max().values}")
print(f"  mhw min: {ds.mhw.min().values}")
ds.close()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
