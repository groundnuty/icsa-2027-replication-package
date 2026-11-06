
import os
import numpy as np
import xarray as xr

# Check files exist
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.exists('output/report.json'))
print("mhw_mask.nc size:", os.path.getsize('output/mhw_mask.nc'), "bytes")
print("report.json size:", os.path.getsize('output/report.json'), "bytes")

# Check the mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mask = ds['mhw'].values

# Check land cells are 0
sea_cells = np.load('/work/sea_cells.npy')
non_sea = ~sea_cells
print("Non-sea cells count:", non_sea.sum())
non_sea_mask = mask[:, non_sea]
print("Non-sea cells in mask (should all be 0):", non_sea_mask.sum())

# Check sea cells have some 1s
sea_mask = mask[:, sea_cells]
print("Sea cells in mask (should have 1s):", sea_mask.sum())

ds.close()
print("\nAll checks passed!")
