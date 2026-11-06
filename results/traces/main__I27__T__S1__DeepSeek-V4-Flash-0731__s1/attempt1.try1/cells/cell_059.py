
import numpy as np
import pandas as pd

# Load data
target_data = np.load('/tmp/target_data.npy')
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
target_times = pd.DatetimeIndex(np.load('/tmp/target_times.npy').astype('datetime64[ns]'))

def date_to_doy(dt):
    days_in_month_fixed = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month_fixed[:dt.month]) + dt.day

# For cell (0, 0), manually verify hot day detection
cell_lat, cell_lon = 0, 0

print(f"Cell ({cell_lat}, {cell_lon}):")
print(f"  Target SST and threshold:")
for i in range(len(target_times)):
    date = target_times[i]
    doy = date_to_doy(date)
    idx = doy - 1
    sst = target_data[i, cell_lat, cell_lon]
    thr = threshold_smooth[cell_lat, cell_lon, idx]
    hot = sst >= thr
    if hot:
        print(f"  Day {i} ({str(date.date())}): SST={sst:.3f}, threshold={thr:.3f}, HOT")

# Verify this matches the hot array
hot = np.load('/tmp/hot.npy')
hot_cell = hot[:, cell_lat, cell_lon]
print(f"\n  Hot days from saved array: {np.where(hot_cell)[0]}")
print(f"  MHW days from saved array: {np.where(np.load('/tmp/mhw.npy')[:, cell_lat, cell_lon])[0]}")
