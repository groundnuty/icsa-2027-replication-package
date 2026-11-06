
import numpy as np
from datetime import datetime, date, timedelta
import xarray as xr

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
time = ds['time'].values
target_time_idx = np.load('/tmp/target_time_idx.npy')

# Get target dates
target_dates = []
for i in target_time_idx:
    t = time[i]
    dt = datetime.utcfromtimestamp(int(t) / 1e9)
    target_dates.append(dt.date())

print("Target dates:", target_dates[0], "to", target_dates[-1])

# Day of year function
def day_of_year(month, day):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

# Map each target date to its doy (1-366) and index (0-365)
target_doy = [day_of_year(d.month, d.day) for d in target_dates]
print("Target doys:", target_doy[0], "to", target_doy[-1])
print("First few:", target_doy[:5])
print("Last few:", target_doy[-5:])

# Store
np.save('/tmp/target_doy.npy', np.array(target_doy))
