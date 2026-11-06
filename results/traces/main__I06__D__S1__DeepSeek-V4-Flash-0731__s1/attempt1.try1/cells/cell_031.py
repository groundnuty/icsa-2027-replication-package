
import numpy as np
import pandas as pd

# Load data
target_sst = np.load('/work/target_sst.npy')
target_time_idx = np.load('/work/target_time_idx.npy')
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
climatologies_smooth = np.load('/work/climatologies_smooth.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
target_dates = time[target_time_idx]
target_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in target_dates]

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

# Examine cell (30, 30)
i, j = 30, 30
sst_cell = target_sst[:, i, j].astype(np.float64)
threshold_cell = np.array([thresholds_smooth[doy-1, i, j] for doy in target_doy])
clim_cell = np.array([climatologies_smooth[doy-1, i, j] for doy in target_doy])

print(f"Cell ({i},{j}) - SST, threshold, climatology, hot:")
for t in range(92):
    hot_flag = sst_cell[t] >= threshold_cell[t]
    print(f"  {target_dates_list[t]} (doy={target_doy[t]}): SST={sst_cell[t]:.4f}, Thresh={threshold_cell[t]:.4f}, Clim={clim_cell[t]:.4f}, Hot={hot_flag}")
