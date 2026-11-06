
import numpy as np
from datetime import datetime

def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Load data
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
target_times = np.load('/work/target_times.npy')
sea_cells = np.load('/work/sea_cells.npy')
threshold_smooth = np.load('/work/threshold_smooth.npy')  # (n_sea, 366)

# Get target dates
target_dates = []
for t in target_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    target_dates.append(dt)
target_dates = np.array(target_dates)

print("Target dates:", target_dates[0], "to", target_dates[-1], "count:", len(target_dates))

# Compute day of year for each target date
target_doy = np.array([doy_fixed(d) for d in target_dates])
print("Target doy range:", target_doy[0], "to", target_doy[-1])

# Get sea cell SST: (92, n_sea)
n_sea = sea_cells.sum()
target_sst_sea = target_sst[:, sea_cells]  # (92, n_sea)

# For each cell and day, check if hot (SST >= threshold)
# threshold_smooth[cell, doy-1]
hot = np.zeros((len(target_dates), n_sea), dtype=bool)
for t_idx, doy in enumerate(target_doy):
    hot[t_idx, :] = target_sst_sea[t_idx, :] >= threshold_smooth[:, doy-1]

print("Hot days per cell: min={}, max={}, mean={:.1f}".format(
    hot.sum(axis=0).min(), hot.sum(axis=0).max(), hot.sum(axis=0).mean()))
print("Active days (any cell hot):", hot.sum(axis=1).sum())
print("Days with at least one hot cell:", (hot.sum(axis=1) > 0).sum())
