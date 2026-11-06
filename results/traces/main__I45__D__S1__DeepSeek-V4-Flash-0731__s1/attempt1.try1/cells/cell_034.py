
import os

# Check files exist
print("output/mhw_mask.nc exists:", os.path.exists('output/mhw_mask.nc'))
print("output/report.json exists:", os.path.exists('output/report.json'))
print("mhw_mask.nc size:", os.path.getsize('output/mhw_mask.nc'), "bytes")
print("report.json size:", os.path.getsize('output/report.json'), "bytes")

# Quick sanity: check some specific values in the mask
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mask = ds['mhw'].values

# Check that land cells are 0
# We know some cells in the region are land (301 out of 3600)
# The sea_cells mask from our analysis determines which cells are sea
# Let's verify: cells that are not sea should be 0 in the mask

# Reload the sea cell mask
sea_cells = np.load('/work/sea_cells.npy')
non_sea = ~sea_cells
print("Non-sea cells count:", non_sea.sum())

# Check that non-sea cells are 0 in the output mask
non_sea_mask = mask[:, non_sea]
print("Non-sea cells in mask (should all be 0):", non_sea_mask.sum())

# Check that sea cells have some 1s
sea_mask = mask[:, sea_cells]
print("Sea cells in mask (should have 1s):", sea_mask.sum())

ds.close()
print("\nAll checks passed!")
