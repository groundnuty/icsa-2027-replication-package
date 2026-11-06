
import numpy as np

tgt_data = np.load('/tmp/tgt_data.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
clim_smooth = np.load('/tmp/clim_smooth.npy')

import pandas as pd

def day_of_year(month, day):
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

tgt_doy = np.array([day_of_year(pd.Timestamp(t).to_pydatetime().month, 
                                pd.Timestamp(t).to_pydatetime().day) for t in tgt_times])

# Sea cells: finite on all target days
sea_mask = np.all(np.isfinite(tgt_data), axis=0)

# For sea cells, check if threshold is finite for all target DOYs
sea_indices = np.where(sea_mask)
all_thresh_finite = True
for i, j in zip(sea_indices[0], sea_indices[1]):
    for doy in tgt_doy:
        if not np.isfinite(threshold_smooth[doy-1, i, j]):
            all_thresh_finite = False
            print(f"Non-finite threshold for cell ({i},{j}), doy {doy}")
            break
    if not all_thresh_finite:
        break

print(f"All sea cells have finite threshold for all target DOYs: {all_thresh_finite}")

# Compute hot days for each sea cell
# hot[t, i, j] = 1 if tgt_data[t, i, j] >= threshold_smooth[tgt_doy[t]-1, i, j]
N_t = len(tgt_times)
hot = np.zeros((N_t, 60, 60), dtype=bool)

for t in range(N_t):
    doy = tgt_doy[t]
    hot[t] = tgt_data[t] >= threshold_smooth[doy-1]

# Set land cells to False
hot = hot & sea_mask

print("Hot day counts per day (sum over all cells):", hot.sum(axis=(1,2)))
print("Total hot day-cell counts:", hot.sum())
