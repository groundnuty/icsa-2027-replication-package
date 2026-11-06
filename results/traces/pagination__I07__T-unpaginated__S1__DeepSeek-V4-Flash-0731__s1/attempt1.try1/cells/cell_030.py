
import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"Dimensions: {dict(ds.dims)}")
print(f"Variables: {list(ds.variables.keys())}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw min/max: {ds.mhw.values.min()}/{ds.mhw.values.max()}")
print(f"Time values: {ds.time.values[:3]} ... {ds.time.values[-3:]}")
print(f"Lat values: {ds.lat.values[:3]} ... {ds.lat.values[-3:]}")
print(f"Lon values: {ds.lon.values[:3]} ... {ds.lon.values[-3:]}")
print(f"mhw sum: {ds.mhw.values.sum()}")
print()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("=== report.json ===")
print(json.dumps(report, indent=2))
print()

# Verify sea cells are correct
sea_cells = np.load('/tmp/sea_cells.npy')
print(f"Sea cells: {sea_cells.sum()}")
print(f"mhw cells with any MHW: {(ds.mhw.values.max(axis=0) > 0).sum()}")
print(f"Land cells: {(~sea_cells).sum()}")
