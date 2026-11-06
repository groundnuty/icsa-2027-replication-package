
import numpy as np
import pandas as pd

sst_target = np.load('sst_target.npy')
threshold_smooth = np.load('threshold_smooth.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')

# Target dates
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 213+30, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Oops, let me use the correct cum_days
def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

target_doy = np.array([day_of_year(d) for d in target_dates])

# Sea cells mask
sea_cells = np.all(~np.isnan(sst_target), axis=0)
print('Sea cells:', sea_cells.sum())

# Compute hot mask: (time, lat, lon), 1 if hot, 0 otherwise (land cells = 0)
n_time, n_lat, n_lon = sst_target.shape
hot_mask = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    doy = target_doy[t]
    thr = threshold_smooth[doy]  # (n_lat, n_lon)
    # Hot if SST >= threshold, and cell is sea cell
    valid = ~np.isnan(sst_target[t]) & ~np.isnan(thr) & sea_cells
    hot_mask[t] = valid & (sst_target[t] >= thr)

print('Hot days total:', hot_mask.sum())
print('Hot day fraction:', hot_mask.mean())
