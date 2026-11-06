
import numpy as np
import pandas as pd

# Re-verify the per-cell MHW detection for a few cells
sst_target = np.load('sst_target.npy')
threshold_smooth = np.load('threshold_smooth.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])
sea_cells = np.all(~np.isnan(sst_target), axis=0)

n_time, n_lat, n_lon = sst_target.shape

# Compute hot mask with explicit float64
hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    thr = threshold_smooth[doy].astype(np.float64)
    sst_t = sst_target[t].astype(np.float64)
    valid = ~np.isnan(sst_t) & ~np.isnan(thr) & sea_cells
    hot_mask[t] = valid & (sst_t >= thr)

print('Hot mask sum:', hot_mask.sum())

# For cell (30,30), show hot days
i, j = 30, 30
if sea_cells[i, j]:
    hot_3030 = hot_mask[:, i, j]
    hot_days = [t for t in range(n_time) if hot_3030[t]]
    print(f'\nCell ({i},{j}): {len(hot_days)} hot days')
    for t in hot_days:
        print(f'  {pd.Timestamp(target_time[t]).strftime("%Y-%m-%d")} (DOY {target_doy[t]})')
