
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

# Find a cell with a long MHW that includes gaps (joined MHWs)
# Look for cells where mhw_mask has gaps (0s) within a single connected run
for la in range(sea_cells.shape[0]):
    for lo in range(sea_cells.shape[1]):
        if sea_cells[la, lo] and np.any(mhw_mask[:, la, lo]):
            cell_mask = mhw_mask[:, la, lo]
            # Check if there are any zeros within a run of ones
            # (i.e., the cell has joined MHWs with gaps)
            # Find runs of mhw values
            transitions = np.diff(np.concatenate([[0], cell_mask, [0]]))
            starts = np.where(transitions == 1)[0]
            ends = np.where(transitions == -1)[0]
            if len(starts) > 1:
                print(f"Cell ({la},{lo}) has {len(starts)} MHW segments (joined)")
                for s, e in zip(starts, ends):
                    print(f"  Segment: {target_dates[s].strftime('%Y-%m-%d')} to {target_dates[e-1].strftime('%Y-%m-%d')}")
                # Print hot days for this cell
                print("  Hot days:")
                for t in range(len(target_time)):
                    doy_idx = target_doy[t] - 1
                    thr = threshold_smooth[doy_idx, la, lo]
                    sst = target_sst[t, la, lo]
                    if sst >= thr:
                        print(f"    {target_dates[t].strftime('%Y-%m-%d')}: SST={sst:.3f}, thr={thr:.3f}, mhw={cell_mask[t]}")
                break
    else:
        continue
    break
