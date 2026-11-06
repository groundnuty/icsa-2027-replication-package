import h5py, numpy as np, xarray as xr
# cross-check h5py region slice vs xarray on the test file
with h5py.File('/work/data/test_20210601.nc','r') as f:
    reg = f['analysed_sst'][0, 130:190, 78:138]
    lat = f['latitude'][130:190]
    lon = f['longitude'][78:138]
    tv = f['time'][0]
ds = xr.open_dataset('/work/data/test_20210601.nc', engine='h5netcdf')
reg_x = ds['analysed_sst'].sel(latitude=slice(56.09,57.29), longitude=slice(10.55,11.75)).values[0]
print('match:', np.array_equal(np.nan_to_num(reg, nan=-999.), np.nan_to_num(reg_x, nan=-999.)))
print('shape:', reg.shape, 'lat[0],lat[-1]:', lat[0], lat[-1], 'lon[0],lon[-1]:', lon[0], lon[-1])
import datetime as dt
print('time value:', tv, '->', dt.datetime(1981,1,1)+dt.timedelta(seconds=int(tv)))
print('n NaN in region:', int(np.isnan(reg).sum()), 'of', reg.size)
ds.close()
