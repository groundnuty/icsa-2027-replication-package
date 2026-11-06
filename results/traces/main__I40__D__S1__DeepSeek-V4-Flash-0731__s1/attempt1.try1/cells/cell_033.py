
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

def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

targ_doy = np.array([date_to_doy(d) for d in targ_dates])

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values

# Find cells active on day 65 (Aug 5)
active_cells_65 = np.where(mhw[65] > 0)
print(f"Active cells on day 65 (Aug 5): {len(active_cells_65[0])}")
for k in range(len(active_cells_65[0])):
    i, j = active_cells_65[0][k], active_cells_65[1][k]
    # Check the hot status and SST for this cell across all target days
    hot_days = []
    for t in range(n_targ):
        d = targ_doy[t]
        sst = target_sst[t, i, j]
        thr = thresholds[d-1, i, j]
        if not np.isnan(sst) and not np.isnan(thr) and sst >= thr:
            hot_days.append(t)
    
    # Check which days the cell is in an MHW (mhw_mask)
    mhw_days = np.where(mhw[:, i, j] > 0)[0]
    
    print(f"\n  Cell ({i},{j}):")
    print(f"    Hot days (0-indexed): {hot_days}")
    print(f"    MHW days (0-indexed): {mhw_days}")
    print(f"    MHW day dates: {[targ_dates[t].strftime('%Y-%m-%d') for t in mhw_days]}")
