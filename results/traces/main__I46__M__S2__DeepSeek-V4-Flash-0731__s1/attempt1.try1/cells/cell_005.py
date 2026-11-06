
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

target_mask = (time >= target_start) & (time <= target_end)
baseline_mask = (time >= baseline_start) & (time <= baseline_end)

print("target indices:", np.where(target_mask)[0][0], np.where(target_mask)[0][-1])
print("n target days:", np.sum(target_mask))
print("baseline indices:", np.where(baseline_mask)[0][0], np.where(baseline_mask)[0][-1])
print("n baseline days:", np.sum(baseline_mask))
