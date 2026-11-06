import xarray as xr, numpy as np
big = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d1 = xr.open_dataset('/work/daily_20100601.nc', engine='h5netcdf')
d2 = xr.open_dataset('/work/daily_19920601.nc', engine='h5netcdf')
print(d1)
print(d2)
# compare coords and data on a slice
lat = big.latitude.values; lon = big.longitude.values
print('lat match:', np.array_equal(lat, d1.latitude.values), np.array_equal(lat, d2.latitude.values))
print('lon match:', np.array_equal(lon, d1.longitude.values), np.array_equal(lon, d2.longitude.values))
sub_big = big.analysed_sst.sel(time='2010-06-01').values
print('data 2010-06-01 equal:', np.array_equal(sub_big, d1.analysed_sst.values, equal_nan=True))
sub_big2 = big.analysed_sst.sel(time='1992-06-01').values
print('data 1992-06-01 equal:', np.array_equal(sub_big2, d2.analysed_sst.values, equal_nan=True))
print('n nan big 20100601:', np.isnan(sub_big).sum(), 'n nan daily:', np.isnan(d1.analysed_sst.values).sum())
