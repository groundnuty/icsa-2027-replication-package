
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

# Region indices
lat_idx = range(34, 94)  # 54.18 to 55.36
lon_idx = range(213, 273)  # 13.26 to 14.44

# Target period: 2014-06-01 to 2014-08-31
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')

# Baseline range with extended windows: 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

time = ds['time'].values
print("Time range:", time[0], time[-1])

# Find time indices
target_mask = (time >= target_start) & (time <= target_end)
baseline_mask = (time >= baseline_start) & (time <= baseline_end)

target_time_idx = np.where(target_mask)[0]
baseline_time_idx = np.where(baseline_mask)[0]

print("Target time indices:", target_time_idx[0], target_time_idx[-1], "count:", len(target_time_idx))
print("Baseline time indices:", baseline_time_idx[0], baseline_time_idx[-1], "count:", len(baseline_time_idx))
print("Target dates:", time[target_time_idx[0]], time[target_time_idx[-1]])
print("Baseline dates:", time[baseline_time_idx[0]], time[baseline_time_idx[-1]])
