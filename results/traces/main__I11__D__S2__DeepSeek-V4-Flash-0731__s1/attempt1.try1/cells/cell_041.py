
import numpy as np
import xarray as xr
import pandas as pd

# Load the mhw_mask output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values  # (time, lat, lon)

# Check cell (0,0) 
cell_mhw = mhw[:, 0, 0]  # time series for cell (0,0)
print("Cell (0,0) MHW pattern:")
for t in range(len(ds.time)):
    if cell_mhw[t] == 1:
        print(f"  {ds.time.values[t]}: MHW=1")

# The expected pattern should be: days 4-11 (MHW 1) and days 18-54 (MHW 2)
# Let me verify the exact indices
print(f"\nSum of MHW for cell (0,0): {cell_mhw.sum()}")
# Expected: 8 (run 4-11) + 37 (run 18-54) = 45
print(f"Expected: 8 + 37 = 45")

# Check some specific days
for day_idx in [4, 5, 10, 11, 12, 17, 18, 30, 54, 55, 56, 57, 58]:
    val = cell_mhw[day_idx]
    date_str = str(ds.time.values[day_idx])[:10]
    print(f"  Day {day_idx} ({date_str}): MHW={val}")
