import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd

# Load all needed data
target_ds = xr.open_dataset('/tmp/target_data.nc')
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
target_time = target_ds['time'].values
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
climatology_smooth = np.load('/tmp/climatology_smooth.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

def day_of_year(date):
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

# Compute DOY for each target date
target_doy = [day_of_year(d) for d in target_dates]
print("Target DOYs:", target_doy)
print("Number of target days:", len(target_dates))

# Check DOYs
for i, d in enumerate(target_dates):
    if i < 5 or i >= len(target_dates)-5:
        print(f"  {d} -> DOY {target_doy[i]}")
