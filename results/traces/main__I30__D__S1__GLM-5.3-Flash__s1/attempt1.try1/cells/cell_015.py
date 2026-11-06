import xarray as xr, numpy as np
big = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d1 = xr.open_dataset('/work/daily_20100601.nc', engine='h5netcdf')
a = big.analysed_sst.sel(time='2010-06-01').values.reshape(1,626,1051)
b = d1.analysed_sst.values
print('identical (equal_nan):', np.array_equal(a, b, equal_nan=True))
print('sst encoding:', {k:v for k,v in big.analysed_sst.encoding.items() if k in ('dtype','chunksizes','contiguous','source','original_shape')})
print('numpy version:', np.__version__)
# region mask
lat = big.latitude.values.astype(np.float64)
lon = big.longitude.values.astype(np.float64)
lat_m = (lat >= 58.69) & (lat <= 59.89)
lon_m = (lon >= 18.69) & (lon <= 19.89)
print('n lat cells:', lat_m.sum(), lat[lat_m][0], lat[lat_m][-1])
print('n lon cells:', lon_m.sum(), lon[lon_m][0], lon[lon_m][-1])
print('spacing check:', np.unique(np.diff(lat[lat_m])), np.unique(np.diff(lon[lon_m])))
