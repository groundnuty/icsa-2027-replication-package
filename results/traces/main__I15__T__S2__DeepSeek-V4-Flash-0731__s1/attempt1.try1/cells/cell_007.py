
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
sst_target = ds.analysed_sst.sel(time=slice(target_start, target_end), latitude=slice(56.13, 57.33), longitude=slice(17.71, 18.91))
sst_target.load()

base_start_ext = np.datetime64('1991-12-27')
base_end_ext = np.datetime64('2003-01-05')
sst_base = ds.analysed_sst.sel(time=slice(base_start_ext, base_end_ext), latitude=slice(56.13, 57.33), longitude=slice(17.71, 18.91))
sst_base.load()

print('Target shape:', sst_target.shape)
print('Baseline shape:', sst_base.shape)
print('Target time:', sst_target.time.values[0], sst_target.time.values[-1])
print('Baseline time:', sst_base.time.values[0], sst_base.time.values[-1])

# Save data for later
import pickle
# Store as numpy arrays
np.save('sst_target.npy', sst_target.values)
np.save('sst_base.npy', sst_base.values)
np.save('target_time.npy', sst_target.time.values.astype('datetime64[D]').astype('int64'))
np.save('base_time.npy', sst_base.time.values.astype('datetime64[D]').astype('int64'))
np.save('lats.npy', sst_target.latitude.values)
np.save('lons.npy', sst_target.longitude.values)
