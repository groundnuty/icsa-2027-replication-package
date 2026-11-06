
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region and relevant times
lat_idx = slice(132, 191)  # 56.14 to 57.32
lon_idx = slice(436, 495)  # 17.72 to 18.9

# Load target period data
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
sst_target = ds.analysed_sst.sel(time=slice(target_start, target_end), latitude=slice(56.13, 57.33), longitude=slice(17.71, 18.91))
print('Target shape:', sst_target.shape)

# Load extended baseline data (1991-12-27 to 2003-01-05)
base_start_ext = np.datetime64('1991-12-27')
base_end_ext = np.datetime64('2003-01-05')
sst_base = ds.analysed_sst.sel(time=slice(base_start_ext, base_end_ext), latitude=slice(56.13, 57.33), longitude=slice(17.71, 18.91))
print('Baseline shape:', sst_base.shape)
