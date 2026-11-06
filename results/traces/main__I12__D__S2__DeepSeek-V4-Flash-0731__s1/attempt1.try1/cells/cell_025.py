
import numpy as np
import pandas as pd
import xarray as xr

# Load the mask
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

# Find cells with interesting patterns (both short and long MHWs)
# Let me count how many cells have MHWs and their durations
n_lat, n_lon = 60, 60
n_target = mhw.shape[0]

cell_mhw_counts = {}
for i in range(n_lat):
    for j in range(n_lon):
        days = np.where(mhw[:, i, j] > 0)[0]
        if len(days) > 0:
            # Find runs
            runs = []
            in_run = False
            for t in range(n_target):
                if mhw[t, i, j] > 0:
                    if not in_run:
                        in_run = True
                        start = t
                else:
                    if in_run:
                        runs.append((start, t-1))
                        in_run = False
            if in_run:
                runs.append((start, n_target-1))
            cell_mhw_counts[(i,j)] = runs

print("Cells with MHWs:", len(cell_mhw_counts))

# Check a few specific cells with their MHW runs
# Sort by number of MHW runs
cell_list = sorted(cell_mhw_counts.items(), key=lambda x: len(x[1]), reverse=True)
print("\nCells with multiple MHW runs:")
for (i,j), runs in cell_list[:5]:
    run_strs = [f"{pd.Timestamp(ds_out.time.values[s]).strftime('%m-%d')}-{pd.Timestamp(ds_out.time.values[e]).strftime('%m-%d')}" for s,e in runs]
    print(f"  Cell ({i},{j}): {run_strs}")
