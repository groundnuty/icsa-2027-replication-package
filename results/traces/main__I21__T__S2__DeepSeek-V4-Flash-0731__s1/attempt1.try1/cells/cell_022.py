
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime

# Load data and intermediate results
threshold_smooth = np.load('threshold_smooth.npy')
sea_cells = np.load('sea_cells.npy')
mhw_mask = np.load('mhw_mask.npy')

target_data = xr.open_dataset('target_data.nc')
target_sst = target_data.analysed_sst.values
target_time = target_data.time.values

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]
target_doy = [day_of_year(dt) for dt in target_dates]

# Pick a specific sea cell and trace through
sea_indices = np.argwhere(sea_cells)
# Pick a cell that has MHW activity
for la, lo in sea_indices[:20]:
    if np.any(mhw_mask[:, la, lo]):
        print(f"\nCell ({la}, {lo}):")
        # Show hot days, thresholds, SST
        for t in range(len(target_time)):
            doy_idx = target_doy[t] - 1
            thr = threshold_smooth[doy_idx, la, lo]
            sst = target_sst[t, la, lo]
            hot_val = sst >= thr
            mhw_val = mhw_mask[t, la, lo]
            if hot_val or mhw_val:
                print(f"  {target_dates[t].strftime('%Y-%m-%d')}: SST={sst:.3f}, thr={thr:.3f}, hot={hot_val}, mhw={mhw_val}")
        break
