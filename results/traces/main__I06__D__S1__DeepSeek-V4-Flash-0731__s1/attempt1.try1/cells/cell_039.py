
import numpy as np
import xarray as xr
import pandas as pd
import datetime

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
time_vals = ds.time.values

# Check cell (9,27) mask
print("Cell (9,27) mask:")
for t in range(92):
    if mhw[t, 9, 27] == 1:
        print(f"  {pd.Timestamp(time_vals[t]).strftime('%Y-%m-%d')}: 1")

# Check cells in MHW on July 25-29 (indices 54-58)
print("\nCells in MHW on July 25 (index 54):")
cells_july = np.argwhere(mhw[54] == 1)
for ci, cj in cells_july:
    print(f"  ({ci}, {cj})")

# Check cell (9,27) hot pattern more carefully
print("\nCell (9,27) mask pattern:")
mask_row = mhw[:, 9, 27]
for t in range(92):
    if mask_row[t] == 1:
        print(f"  Day {t}: {pd.Timestamp(time_vals[t]).strftime('%Y-%m-%d')}")

# Check July cells
print("\nCells in MHW on July 27 (index 56):")
cells_jul27 = np.argwhere(mhw[56] == 1)
for ci, cj in cells_jul27:
    print(f"  ({ci}, {cj})")

# Examine the cells in MHWs during July event
print("\nExamining cells in July event:")
for ci, cj in cells_july:
    print(f"\n  Cell ({ci}, {cj}):")
    mask_row = mhw[:, ci, cj]
    hot_days = np.where(mask_row == 1)[0]
    print(f"  MHW days: {[pd.Timestamp(time_vals[t]).strftime('%Y-%m-%d') for t in hot_days]}")
