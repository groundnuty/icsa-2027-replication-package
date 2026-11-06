
import numpy as np
import pandas as pd
import xarray as xr

# Let me look at the per-cell MHW detection more carefully
# Load the mask and check if any cells have gap days included

ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds_out['mhw'].values

# For each cell with an MHW, check if the MHW days include non-contiguous hot days
# (i.e., the MHW includes gap days)

# Actually, let me check if there are cells where the MHW pattern has internal non-hot days
# Since the mask marks ALL days in the MHW (including gaps), we need to check
# whether any MHW run has non-hot days inside it.

# But I already computed the hot days separately. Let me just check if any MHW has 
# non-contiguous days by looking at the pattern

n_target, n_lat, n_lon = mhw.shape

# Check if any cell has multiple disjoint MHW periods (which would indicate joining)
for i in range(n_lat):
    for j in range(n_lon):
        pattern = mhw[:, i, j]
        if pattern.sum() > 0:
            # Find transitions
            transitions = 0
            for t in range(1, n_target):
                if pattern[t] != pattern[t-1]:
                    transitions += 1
            # If it starts and ends with 1, it should have even transitions
            # (0->1, 1->0, 0->1, 1->0 = 4 transitions for 2 MHWs)
            if transitions > 2:
                print(f"Cell ({i},{j}): {transitions} transitions, pattern includes joining")
