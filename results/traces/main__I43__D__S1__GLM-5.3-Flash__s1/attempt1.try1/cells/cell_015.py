import xarray as xr, numpy as np
ds = xr.open_dataset('/work/dl/sst_19920101.nc', engine='h5netcdf')
sst = ds['analysed_sst'].values[0]
print('nan frac full grid:', np.isnan(sst).mean())
latm = (ds['latitude'].values.astype('float64') >= 62.25-1e-9) & (ds['latitude'].values.astype('float64') <= 63.45+1e-9)
lonm = (ds['longitude'].values.astype('float64') >= 18.73-1e-9) & (ds['longitude'].values.astype('float64') <= 19.93+1e-9)
sub = sst[np.ix_(latm, lonm)]
print('region shape', sub.shape, 'nan frac in region:', np.isnan(sub).mean())
print('SST range in region:', np.nanmin(sub), np.nanmax(sub))
ds2 = xr.open_dataset('/work/test/sst_20170601.nc', engine='h5netcdf')
lat2 = ds2['latitude'].values.astype('float64'); lon2 = ds2['longitude'].values.astype('float64')
print('coords equal across files:', np.array_equal(ds['latitude'].values, ds2['latitude'].values), np.array_equal(ds['longitude'].values, ds2['longitude'].values))
