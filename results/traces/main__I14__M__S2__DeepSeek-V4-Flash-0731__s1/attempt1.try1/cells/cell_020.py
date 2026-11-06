
import numpy as np
import pandas as pd

sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_indices = np.load('/tmp/target_indices.npy')

def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

times_np = times.values
target_mask = (times_np >= np.datetime64('2015-06-01')) & (times_np <= np.datetime64('2015-08-31'))
target_indices = np.where(target_mask)[0]
target_doy = np.array([compute_doy(times[i].month, times[i].day) for i in target_indices])

# Find cells where hot runs are separated by 1-2 non-hot days and need joining
# Let me check hot patterns directly

hot_all = np.zeros_like(mhw_mask)
for ci, (lat, lon) in enumerate(sea_cells):
    sst_cell = sst_data[target_indices, lat, lon]
    thresh_cell = thresholds_smoothed[target_doy - 1, lat, lon]
    hot_all[ci, :] = (sst_cell >= thresh_cell).astype(np.int8)

# Find cells where the MHW mask differs from the raw hot pattern
diff = mhw_mask != hot_all
cells_with_diff = np.where(diff.any(axis=1))[0]
print("Cells where MHW mask differs from hot pattern:", len(cells_with_diff))

# For cells where MHW mask != hot pattern, check if it's due to joining
for ci in cells_with_diff[:10]:
    lat, lon = sea_cells[ci]
    h = hot_all[ci, :]
    m = mhw_mask[ci, :]
    # Find hot runs
    runs = []
    i = 0
    n = len(h)
    while i < n:
        if h[i] == 1:
            j = i
            while j < n and h[j] == 1:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    print(f"\nCell ({lat},{lon}): hot runs = {runs}")
    print(f"  MHW mask: {m}")
