
import numpy as np
import pandas as pd
import xarray as xr

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

# Find which cells have MHW starting on June 24 (index 23)
day_24_idx = 23  # June 24 = index 23 (June 1 = index 0)

# For each cell, check if mhw is active on that day
cells_on_24 = np.where(mhw[day_24_idx] > 0)
print(f"Cells with MHW on June 24: {len(cells_on_24[0])}")

# Check if these are isolated or part of longer MHWs
for k in range(min(5, len(cells_on_24[0]))):
    i, j = cells_on_24[0][k], cells_on_24[1][k]
    pattern = mhw[:, i, j]
    # Find the run containing day 24
    # Check if it's contiguous
    idxs = np.where(pattern > 0)[0]
    print(f"  Cell ({i},{j}): MHW days = {idxs[0]} to {idxs[-1]}")
