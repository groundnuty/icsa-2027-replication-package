
import xarray as xr
import numpy as np
import json

# Read back the mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Mask file contents:")
print(ds)
print(f"\nVariable mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw unique values: {np.unique(ds.mhw.values)}")
print(f"mhw sum: {ds.mhw.values.sum()}")

# Check dimensions
print(f"\nTime: {ds.time.values[:3]} ... {ds.time.values[-3:]}")
print(f"Lat: {ds.lat.values[:3]} ... {ds.lat.values[-3:]}")
print(f"Lon: {ds.lon.values[:3]} ... {ds.lon.values[-3:]}")
ds.close()

# Read back the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport:")
print(json.dumps(report, indent=2))

# Check that land cells are 0 in the mask
# Sea cells should match per_cell_mhw
sea_cells = np.load('/tmp/sea_cells.npy')
per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')

# Re-read the mask from file
ds2 = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mask = ds2.mhw.values
ds2.close()

# Verify land cells are all 0
land_mask = ~sea_cells
print(f"\nLand cells that are 1 in mask: {(mask[:, land_mask] == 1).sum()}")
print(f"Sea cells MHW sum: {per_cell_mhw.sum()}")
print(f"Mask sum: {mask.sum()}")
print(f"Match: {np.array_equal(mask.astype(bool), per_cell_mhw)}")
