
import fsspec
import xarray as xr
import numpy as np
import time

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
t0 = time.time()
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
data = ds['analysed_sst'].values[0, 157:217, 562:622].astype(np.float64)
print('Time to read one file:', time.time() - t0)
print(data.shape)
print('NaN fraction:', np.isnan(data).mean())
