import xarray as xr, numpy as np
big = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d1 = xr.open_dataset('/work/daily_20100601.nc', engine='h5netcdf')
a = big.analysed_sst.sel(time='2010-06-01').values
b = d1.analysed_sst.values
print('shapes:', a.shape, b.shape)
na, nb = np.isnan(a), np.isnan(b)
print('nan pattern equal:', np.array_equal(na, nb))
print('na count', na.sum(), 'nb count', nb.sum())
# maybe -inf / +inf or other special values?
print('isinf a:', np.isinf(a).sum(), 'b:', np.isinf(b).sum())
print('a unique non-nan min/max:', np.nanmin(a), np.nanmax(a))
print('b unique non-nan min/max:', np.nanmin(b), np.nanmax(b))
# check equality again with float64
print('array_equal equal_nan:', np.array_equal(a.astype(np.float64), b.astype(np.float64), equal_nan=True))
