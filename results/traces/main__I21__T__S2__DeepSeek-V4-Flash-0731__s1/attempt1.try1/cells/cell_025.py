
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

# Let me check: for each cell, trace the hot runs and MHW detection
# Verify that joining is correct
for la in range(sea_cells.shape[0]):
    for lo in range(sea_cells.shape[1]):
        if not sea_cells[la, lo]:
            continue
        
        # Compute hot days
        hot_series = np.zeros(len(target_time), dtype=bool)
        for t in range(len(target_time)):
            doy_idx = target_doy[t] - 1
            thr = threshold_smooth[doy_idx, la, lo]
            sst = target_sst[t, la, lo]
            if np.isfinite(sst) and sst >= thr:
                hot_series[t] = True
        
        # Find all hot runs
        all_runs = []
        i = 0
        while i < len(target_time):
            if hot_series[i]:
                start = i
                while i < len(target_time) and hot_series[i]:
                    i += 1
                all_runs.append((start, i-1))
            else:
                i += 1
        
        # MHWs are runs >= 5
        mhws = [(s, e) for s, e in all_runs if (e - s + 1) >= 5]
        
        if len(mhws) >= 2:
            # Check if any are joined (gap <= 2)
            for idx in range(1, len(mhws)):
                gap = mhws[idx][0] - mhws[idx-1][1] - 1
                if gap <= 2:
                    print(f"Cell ({la},{lo}): MHW1={target_dates[mhws[idx-1][0]].strftime('%m-%d')} to {target_dates[mhws[idx-1][1]].strftime('%m-%d')}, "
                          f"MHW2={target_dates[mhws[idx][0]].strftime('%m-%d')} to {target_dates[mhws[idx][1]].strftime('%m-%d')}, gap={gap}")
                    print(f"  Hot runs: {[(target_dates[s].strftime('%m-%d'), target_dates[e].strftime('%m-%d'), e-s+1) for s, e in all_runs]}")
                    break
            else:
                continue
            break
    else:
        continue
    break
