
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

# Find cells with MHW
active_per_cell = mhw_mask.sum(axis=1)
cells_with_mhw = np.where(active_per_cell > 0)[0]
print("Cells with MHW:", len(cells_with_mhw))

# Look at a few
for ci in cells_with_mhw[:10]:
    lat, lon = sea_cells[ci]
    sst_cell = sst_data[target_indices, lat, lon]
    thresh_cell = thresholds_smoothed[target_doy - 1, lat, lon]
    hot = (sst_cell >= thresh_cell).astype(int)
    
    # Find hot runs
    runs = []
    i = 0
    while i < len(hot):
        if hot[i] == 1:
            j = i
            while j < len(hot) and hot[j] == 1:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    
    print(f"Cell ({lat},{lon}): hot runs = {runs}")
    print(f"  MHW days (target indices): {np.where(mhw_mask[ci] > 0)[0]}")
    # Map to dates
    mhw_days = np.where(mhw_mask[ci] > 0)[0]
    dates = [times[target_indices[d]].date() for d in mhw_days]
    print(f"  MHW dates: {dates}")
    print()
