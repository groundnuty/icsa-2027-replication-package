import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print('---')
lat = ds['latitude'].values
lon = ds['longitude'].values
time = ds['time'].values
print('lat dtype', lat.dtype, 'range', lat.min(), lat.max())
print('lon dtype', lon.dtype, 'range', lon.min(), lon.max())
print('time first/last', time[0], time[-1], 'count', len(time))
# check time regularity: all daily
dts = np.diff(time).astype('timedelta64[D]').astype(int)
print('unique time steps (days):', np.unique(dts))
