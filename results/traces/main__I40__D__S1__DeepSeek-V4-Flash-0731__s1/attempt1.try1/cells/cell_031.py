
import xarray as xr
import numpy as np

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
print(f"mhw shape: {mhw.shape}, dtype: {mhw.dtype}")
print(f"mhw values: {np.unique(mhw)}")

# Check that land cells are 0
# Land cells should be the non-sea cells
# From our earlier analysis, 292 cells are non-sea (land)

# Check: on any day, what cells have mhw=1?
# Sum over time for each cell
cell_sum = mhw.sum(axis=0)
print(f"Cell sum (MHW days per cell) range: {cell_sum.min()} to {cell_sum.max()}")

# Count cells that are never in MHW
never_mhw = np.sum(cell_sum == 0)
print(f"Cells never in MHW: {never_mhw}")

# Count cells that are in MHW at least once
ever_mhw = np.sum(cell_sum > 0)
print(f"Cells in MHW at least once: {ever_mhw}")

# Check the time dimension
print(f"\nTime values: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time)}")

# Verify the mask is correct by checking specific days
# Regional event 1: days 25-34 (indices in the mask should match)
# June 26 = day 25 (0-indexed), July 5 = day 34
print(f"\nDay 25 (2009-06-26): {mhw[25].sum()} cells active")
print(f"Day 24 (2009-06-25): {mhw[24].sum()} cells active")
print(f"Day 35 (2009-07-06): {mhw[35].sum()} cells active")

# Regional event 2: days 65-72
print(f"Day 65 (2009-08-05): {mhw[65].sum()} cells active")
print(f"Day 64 (2009-08-04): {mhw[64].sum()} cells active")
print(f"Day 73 (2009-08-13): {mhw[73].sum()} cells active")
