
import numpy as np
import xarray as xr
import pandas as pd

target_data = xr.open_dataset('target_data.nc')
thresholds_smooth = np.load('thresholds_smooth.npy')

target_sst = target_data.analysed_sst.values
target_time = target_data.time.values
n_days, n_lat, n_lon = target_sst.shape

cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

target_dates = [pd.Timestamp(t).date() for t in target_time.astype('datetime64[D]')]
target_doys = [date_to_doy(d.year, d.month, d.day) for d in target_dates]

sea_mask = np.all(~np.isnan(target_sst), axis=0)
i, j = 30, 30

sst_cell = target_sst[:, i, j]
thresh_cell = np.array([thresholds_smooth[doy, i, j] for doy in target_doys])
hot_cell = sst_cell >= thresh_cell

print("Days 45-55:")
for d in range(45, 56):
    print(f"  Day {d} ({target_dates[d]}): SST={sst_cell[d]:.4f}, Thresh={thresh_cell[d]:.4f}, Hot={hot_cell[d]}")

print("\nDays 70-80:")
for d in range(70, 81):
    print(f"  Day {d} ({target_dates[d]}): SST={sst_cell[d]:.4f}, Thresh={thresh_cell[d]:.4f}, Hot={hot_cell[d]}")
