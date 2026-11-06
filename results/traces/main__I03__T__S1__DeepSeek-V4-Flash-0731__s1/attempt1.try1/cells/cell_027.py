
import numpy as np
import datetime

# Load data
target_vals = np.load('target_vals.npy').astype(np.float64)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
threshold_smooth = np.load('threshold_smooth.npy')
sea_cells = np.load('sea_cells.npy')
mhw_mask = np.load('mhw_mask_per_cell.npy')

target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Find a cell that has many MHW days
cell_mhw_count = mhw_mask.sum(axis=0)
# Find the cell with most MHW days
max_cell = np.unravel_index(np.argmax(cell_mhw_count), cell_mhw_count.shape)
lat_i, lon_i = max_cell
print(f"Cell with most MHW days: ({lat_i}, {lon_i}), count={cell_mhw_count[lat_i, lon_i]}")

# Check if it's a sea cell
print(f"Is sea cell: {sea_cells[lat_i, lon_i]}")

# Print hot days and MHW pattern
hot = np.zeros(92, dtype=bool)
for t in range(92):
    doy = day_of_year(target_dt[t])
    sst = target_vals[t, lat_i, lon_i]
    thresh = threshold_smooth[doy, lat_i, lon_i]
    hot[t] = sst >= thresh

print("\nHot days:")
for t in range(92):
    if hot[t]:
        print(f"  Day {t} ({target_dt[t].strftime('%Y-%m-%d')}): hot, MHW={bool(mhw_mask[t, lat_i, lon_i])}")
    elif mhw_mask[t, lat_i, lon_i]:
        print(f"  Day {t} ({target_dt[t].strftime('%Y-%m-%d')}): NOT hot, but MHW (gap day)")
