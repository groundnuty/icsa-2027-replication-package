
import numpy as np
import datetime

# Load data
target_vals = np.load('target_vals.npy').astype(np.float64)
target_dates_str = np.load('target_dates.npy', allow_pickle=True)
threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')
sea_cells = np.load('sea_cells.npy')
mhw_mask = np.load('mhw_mask_per_cell.npy')

target_dt = [datetime.datetime.strptime(str(s), '%Y-%m-%d') for s in target_dates_str]

def day_of_year(dt):
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Pick a sea cell
sea_idx = np.where(sea_cells)
lat_i = sea_idx[0][0]
lon_i = sea_idx[1][0]
print(f"Cell ({lat_i}, {lon_i}): lat={lat_vals[lat_i]}, lon={lon_vals[lon_i]}")
print(f"SST values (first 20 target days):")
for t in range(20):
    doy = day_of_year(target_dt[t])
    sst = target_vals[t, lat_i, lon_i]
    thresh = threshold_smooth[doy, lat_i, lon_i]
    clim = climatology_smooth[doy, lat_i, lon_i]
    hot_flag = "HOT" if sst >= thresh else "   "
    print(f"  Day {t}: {target_dt[t].strftime('%Y-%m-%d')} doy={doy} sst={sst:.4f} thresh={thresh:.4f} clim={clim:.4f} {hot_flag}")
