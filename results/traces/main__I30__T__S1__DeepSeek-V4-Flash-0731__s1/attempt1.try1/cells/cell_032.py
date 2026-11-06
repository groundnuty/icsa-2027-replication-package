
import numpy as np
import pandas as pd

mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_data = np.load('/tmp/target_data.npy').astype(np.float64)
target_times = np.load('/tmp/target_times.npy').astype('datetime64[D]')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')

# Find cells in MHW on day 26
n_time, n_lat, n_lon = mhw_mask.shape
active_cells_day26 = np.where(mhw_mask[26] > 0)
print("Cells in MHW on day 26:", list(zip(active_cells_day26[0], active_cells_day26[1])))

# For each such cell, check hot pattern around days 20-31
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

target_doy = np.array([day_of_year(pd.Timestamp(t).month, pd.Timestamp(t).day) for t in target_times])

for k in range(len(active_cells_day26[0])):
    i, j = active_cells_day26[0][k], active_cells_day26[1][k]
    print(f"\nCell ({i}, {j}):")
    print("  Days 20-31 (inclusive):")
    for t in range(20, min(32, n_time)):
        sst = target_data[t, i, j]
        doy = target_doy[t]
        thr = threshold_smooth[doy-1, i, j]
        is_hot = sst >= thr
        in_mhw = mhw_mask[t, i, j] > 0
        date_str = pd.Timestamp(target_times[t]).strftime('%m-%d')
        print(f"    Day {t} ({date_str}): SST={sst:.2f}, threshold={thr:.2f}, hot={is_hot}, mhw={in_mhw}")
