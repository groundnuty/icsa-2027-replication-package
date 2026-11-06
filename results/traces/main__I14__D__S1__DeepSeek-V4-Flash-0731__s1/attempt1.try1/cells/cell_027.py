
import numpy as np
import pandas as pd

target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
per_cell_mhw = np.load('/work/per_cell_mhw.npy')

# How many cells have at least one MHW
cells_with_mhw = np.any(per_cell_mhw, axis=0)
print(f"Cells with at least one MHW: {cells_with_mhw.sum()}")

# For each day, how many cells are in an MHW
for t in range(len(target_pd)):
    count = np.sum(per_cell_mhw[t])
    if count > 0:
        print(f"{target_pd[t].date()}: {count} cells in MHW")

# Regional active days
active = np.any(per_cell_mhw, axis=(1, 2))
print(f"\nActive days: {[str(target_pd[t].date()) for t in range(len(target_pd)) if active[t]]}")
