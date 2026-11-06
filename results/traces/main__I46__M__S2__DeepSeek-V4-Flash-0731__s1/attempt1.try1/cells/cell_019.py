
import xarray as xr
import numpy as np
from datetime import date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
time = ds.time.values

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_time = time[target_time_idx]

# Convert to dates
def npdt_to_date(t):
    dt = t.astype('datetime64[D]').astype(object)
    return date(dt.year, dt.month, dt.day)

target_dates = [npdt_to_date(t) for t in target_time]
print("Target dates:")
for i, d in enumerate(target_dates):
    print(f"  Day {i}: {d}")

print()
print("First date:", target_dates[0])
print("Last date:", target_dates[-1])
print("Event start:", target_dates[0])
print("Event end:", target_dates[30])
