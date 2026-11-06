
import numpy as np
import pandas as pd
import xarray as xr

# Load data
target_sst = np.load('/work/target_sst.npy')
targ_times = np.load('/work/targ_times.npy')
thresholds = np.load('/work/thresholds.npy')
targ_dates = pd.DatetimeIndex(targ_times)

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
n_targ = len(targ_dates)

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Find all cells that are in MHWs on any day from 65 to 72
cells_in_event2 = set()
for t in range(65, 73):
    active = np.where(mhw[t] > 0)
    for k in range(len(active[0])):
        cells_in_event2.add((active[0][k], active[1][k]))

print(f"Cells in event 2 (Aug 5-12): {len(cells_in_event2)}")
for (i, j) in sorted(cells_in_event2):
    mhw_days = np.where(mhw[:, i, j] > 0)[0]
    print(f"  Cell ({i},{j}): MHW days = {mhw_days}, dates = {[targ_dates[t].strftime('%m-%d') for t in mhw_days]}")
