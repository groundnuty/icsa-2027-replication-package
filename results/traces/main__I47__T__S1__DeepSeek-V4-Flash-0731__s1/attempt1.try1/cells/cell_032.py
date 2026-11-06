
import numpy as np
import xarray as xr
import pandas as pd

# Load the output
ds = xr.open_dataset('output/mhw_mask.nc')
mhw = ds['mhw'].values  # (92, 60, 60)

# Pick a cell that's in an MHW during the second event (around day 49-58)
# Find a cell that's active on day 49 (July 20)
day49 = mhw[49]  # (60, 60)
active_cells_49 = np.where(day49 > 0)
print(f"Cells in MHW on day 49: {len(active_cells_49[0])}")

if len(active_cells_49[0]) > 0:
    i, j = active_cells_49[0][0], active_cells_49[1][0]
    print(f"Example cell: ({i}, {j}) = lat {ds.lat.values[i]:.2f}, lon {ds.lon.values[j]:.2f}")
    
    # Check MHW mask for this cell over the target period
    cell_mhw = mhw[:, i, j]
    hot_runs = []
    t = 0
    while t < 92:
        if cell_mhw[t]:
            start = t
            while t < 92 and cell_mhw[t]:
                t += 1
            hot_runs.append((start, t-1))
        else:
            t += 1
    
    print(f"MHW periods for this cell:")
    for start, end in hot_runs:
        onset = str(ds.time.values[start])[:10]
        end_date = str(ds.time.values[end])[:10]
        print(f"  {onset} to {end_date} (days {start}-{end}, length {end-start+1})")

# Also check a cell in the first event
day5 = mhw[5]
active_cells_5 = np.where(day5 > 0)
print(f"\nCells in MHW on day 5: {len(active_cells_5[0])}")

if len(active_cells_5[0]) > 0:
    i, j = active_cells_5[0][0], active_cells_5[1][0]
    cell_mhw = mhw[:, i, j]
    hot_runs = []
    t = 0
    while t < 92:
        if cell_mhw[t]:
            start = t
            while t < 92 and cell_mhw[t]:
                t += 1
            hot_runs.append((start, t-1))
        else:
            t += 1
    
    print(f"MHW periods for cell ({i}, {j}):")
    for start, end in hot_runs:
        onset = str(ds.time.values[start])[:10]
        end_date = str(ds.time.values[end])[:10]
        print(f"  {onset} to {end_date} (days {start}-{end}, length {end-start+1})")

# Check how many cells are in MHWs at all
cells_in_mhw = (mhw.sum(axis=0) > 0).sum()
print(f"\nTotal cells that are in at least one MHW: {cells_in_mhw}")
