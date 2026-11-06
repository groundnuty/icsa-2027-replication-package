
import numpy as np
import pandas as pd

sst_target = np.load('sst_target.npy')
threshold_smooth = np.load('threshold_smooth.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
sea_cells = np.load('sea_cells.npy')
per_cell_mhw = np.load('per_cell_mhw.npy')

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])

# Check cell (0,0)
i, j = 0, 0
print(f'Cell ({i},{j}): sea_cell={sea_cells[i,j]}')

# Show hot days and threshold
print('\nDay-by-day analysis for cell (0,0):')
for t in range(len(target_doy)):
    doy = target_doy[t]
    thr = threshold_smooth[doy, i, j]
    sst_val = sst_target[t, i, j]
    hot = not np.isnan(sst_val) and not np.isnan(thr) and sst_val >= thr
    mhw = per_cell_mhw[t, i, j]
    date_str = pd.Timestamp(target_time[t]).strftime('%m-%d')
    print(f'  {date_str}: SST={sst_val:.2f}, thr={thr:.2f}, hot={hot}, mhw={mhw}')
