
import numpy as np
import pandas as pd
import xarray as xr

# Load data
thresholds_smooth = np.load('/work/thresholds_smooth.npy')
sea_cells = np.load('/work/sea_cells.npy')

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_times = target_data.time.values
target_data64 = target_data.values.astype(np.float64)

def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

target_doy = np.array([doy_from_datetime64(t) for t in target_times])
threshold_for_target = thresholds_smooth[target_doy - 1, :, :]

# Cell (37,1)
i, j = 37, 1
print(f"Cell ({i},{j}): lat={ds.latitude.values[260+i]}, lon={ds.longitude.values[485+j]}")

print("\nSST vs threshold for June 15-25, 2017:")
for t in range(92):
    dt = pd.Timestamp(target_times[t])
    if 15 <= dt.day <= 25 and dt.month == 6:
        sst = target_data64[t, i, j]
        thresh = threshold_for_target[t, i, j]
        doy = target_doy[t]
        hot = sst >= thresh
        print(f"  {dt.date()}: DOY={doy}, SST={sst:.2f}, Threshold={thresh:.2f}, Hot={hot}")

print("\nSST vs threshold for July 5-15, 2017:")
for t in range(92):
    dt = pd.Timestamp(target_times[t])
    if 5 <= dt.day <= 15 and dt.month == 7:
        sst = target_data64[t, i, j]
        thresh = threshold_for_target[t, i, j]
        doy = target_doy[t]
        hot = sst >= thresh
        print(f"  {dt.date()}: DOY={doy}, SST={sst:.2f}, Threshold={thresh:.2f}, Hot={hot}")
