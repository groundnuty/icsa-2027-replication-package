
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

# Check cell (6,3)
lat, lon = 6, 3
sst_cell = sst_data[target_indices, lat, lon]
thresh_cell = thresholds_smoothed[target_doy - 1, lat, lon]
hot = (sst_cell >= thresh_cell).astype(int)
print("Cell (6,3) hot pattern (days 25-40):")
print("  Hot:", hot[25:40])
print("  MHW:", mhw_mask[6*60+3, 25:40])  # index in sea_cells?
# Find the index in sea_cells
ci = np.where((sea_cells[:, 0] == 6) & (sea_cells[:, 1] == 3))[0]
print("  Sea cell index:", ci)
if len(ci) > 0:
    print("  MHW mask (sea cell index):", mhw_mask[ci[0], 25:40])
    print("  SST:", sst_cell[25:40])
    print("  Threshold:", thresh_cell[25:40])

# Cells active on day 37
cells_on_37 = np.where(mhw_mask[:, 37] > 0)[0]
print(f"\nCells active on day 37 (July 8): {len(cells_on_37)}")
for ci2 in cells_on_37:
    lat2, lon2 = sea_cells[ci2]
    print(f"  Cell ({lat2},{lon2}): MHW days = {np.where(mhw_mask[ci2] > 0)[0]}")
