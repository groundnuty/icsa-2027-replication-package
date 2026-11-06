
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

lat_i, lon_i = 24, 47

hot = np.zeros(92, dtype=bool)
for t in range(92):
    doy = day_of_year(target_dt[t])
    sst = target_vals[t, lat_i, lon_i]
    thresh = threshold_smooth[doy, lat_i, lon_i]
    hot[t] = sst >= thresh

# Print days 42-55
print("Days 42-55:")
for t in range(42, 56):
    doy = day_of_year(target_dt[t])
    sst = target_vals[t, lat_i, lon_i]
    thresh = threshold_smooth[doy, lat_i, lon_i]
    hot_flag = "HOT" if hot[t] else "   "
    mhw_flag = "MHW" if mhw_mask[t, lat_i, lon_i] else ""
    print(f"  Day {t} ({target_dt[t].strftime('%Y-%m-%d')}): sst={sst:.4f} thresh={thresh:.4f} {hot_flag} {mhw_flag}")

# Print all hot days
print("\nAll hot days:")
for t in range(92):
    if hot[t]:
        print(f"  Day {t} ({target_dt[t].strftime('%Y-%m-%d')}) hot, MHW={bool(mhw_mask[t, lat_i, lon_i])}")
