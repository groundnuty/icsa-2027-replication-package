
import numpy as np
import xarray as xr
import pandas as pd
import datetime

# Load the output mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values
time_vals = ds.time.values

# Find cells in MHWs on June 11 (index 10)
idx_11 = 10
cells_11 = np.argwhere(mhw[idx_11] == 1)
print(f"Cells in MHW on {pd.Timestamp(time_vals[idx_11]).strftime('%Y-%m-%d')}: {len(cells_11)}")
for ci, cj in cells_11:
    print(f"  Cell ({ci}, {cj})")

# Load hot data
target_sst = np.load('/work/target_sst.npy')
target_time_idx = np.load('/work/target_time_idx.npy')
lat_idx = np.load('/work/lat_idx.npy')
lon_idx = np.load('/work/lon_idx.npy')

# Load the s2 file for coordinates and thresholds
ds2 = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_full = ds2.time.values
target_dates_full = time_full[target_time_idx]
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates_full]
ds2.close()

# Recompute hot data for these cells
thresholds_smooth = np.load('/work/thresholds_smooth.npy')

def doy_from_date(date):
    m = date.month; d = date.day
    if m == 1: return d
    elif m == 2: return 31 + d
    elif m == 3: return 60 + d
    elif m == 4: return 91 + d
    elif m == 5: return 121 + d
    elif m == 6: return 152 + d
    elif m == 7: return 182 + d
    elif m == 8: return 213 + d
    elif m == 9: return 244 + d
    elif m == 10: return 274 + d
    elif m == 11: return 305 + d
    elif m == 12: return 335 + d

target_doy = [doy_from_date(d) for d in target_dates_list]
n_target = len(target_dates_list)

target_sst64 = target_sst.astype(np.float64)

# Check hot pattern for each cell in MHW on June 11
for ci, cj in cells_11:
    print(f"\nCell ({ci}, {cj}):")
    hot_series = []
    for t in range(n_target):
        doy = target_doy[t]
        thresh = thresholds_smooth[doy-1, ci, cj]
        sst = target_sst64[t, ci, cj]
        is_hot = sst >= thresh
        hot_series.append(is_hot)
        if t >= 5 and t <= 20:
            print(f"  {target_dates_list[t]}: SST={sst:.4f}, Thresh={thresh:.4f}, Hot={is_hot}")
    
    # Find runs
    hot_arr = np.array(hot_series)
    print(f"  Hot days: {np.where(hot_arr)[0]}")
