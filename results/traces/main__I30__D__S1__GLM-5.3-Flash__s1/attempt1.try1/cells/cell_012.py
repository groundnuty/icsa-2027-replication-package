import xarray as xr, numpy as np
big = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
d1 = xr.open_dataset('/work/daily_20100601.nc', engine='h5netcdf')
a = big.analysed_sst.sel(time='2010-06-01').values.astype(np.float64)
b = d1.analysed_sst.values.astype(np.float64)
both_nan = np.isnan(a) & np.isnan(b)
print('nan pattern identical:', np.array_equal(np.isnan(a), np.isnan(b)))
diff = np.abs(a-b)
m = ~np.isnan(a) & ~np.isnan(b)
print('max abs diff (valid both):', np.nanmax(diff[m]))
print('n differing >0:', (diff[m]>0).sum(), 'of', m.sum())
print('mean abs diff:', diff[m].mean())
# sample values
idx = np.argwhere(m)[:5]
for i,j in idx:
    print(a[i,j], b[i,j])
# check attrs of daily file
print(d1.attrs.get('copernicus_marine_dataset_version'), d1.attrs.get('copernicus_marine_download_date'))
print(big.attrs.get('copernicus_marine_dataset_version'), big.attrs.get('copernicus_marine_download_date'))
print(d1.attrs.get('comment'))
print(big.attrs.get('comment'))
