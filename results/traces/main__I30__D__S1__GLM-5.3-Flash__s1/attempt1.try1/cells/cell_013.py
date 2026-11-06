import xarray as xr, numpy as np
big = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d1 = xr.open_dataset('/work/daily_20100601.nc', engine='h5netcdf')
d2 = xr.open_dataset('/work/daily_19920601.nc', engine='h5netcdf')
a = big.analysed_sst.sel(time='2010-06-01').values
b = d1.analysed_sst.values
print('20100601: nan in s2z:', np.isnan(a).sum(), 'nan in s1z:', np.isnan(b).sum())
c = big.analysed_sst.sel(time='1992-06-01').values
e = d2.analysed_sst.values
print('19920601: nan in s2z:', np.isnan(c).sum(), 'nan in s1z:', np.isnan(e).sum())
# where does s1z have data but s2z nan, and vice versa?
only_s1 = np.isnan(a) & ~np.isnan(b)
only_s2 = ~np.isnan(a) & np.isnan(b)
print('only s1z valid:', only_s1.sum(), 'only s2z valid:', only_s2.sum())
# check land mask: value over land?
print('comment s1z:', d1.attrs['comment'][:300])
print('comment s2z:', big.attrs['comment'][:300])
