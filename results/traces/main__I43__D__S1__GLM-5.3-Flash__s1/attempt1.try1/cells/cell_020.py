import xarray as xr, numpy as np
ds3 = xr.open_dataset('/work/nc/sst_20030105.nc', engine='h5netcdf')
ds1 = xr.open_dataset('/work/nc/sst_19920101.nc', engine='h5netcdf')
print('coords same 2003 vs 1992:', np.array_equal(ds3['latitude'].values, ds1['latitude'].values), np.array_equal(ds3['longitude'].values, ds1['longitude'].values))
lat = ds3['latitude'].values.astype('float64'); lon = ds3['longitude'].values.astype('float64')
latm = (lat >= 62.25-1e-9) & (lat <= 63.45+1e-9)
lonm = (lon >= 18.73-1e-9) & (lon <= 19.93+1e-9)
print('region cells:', latm.sum()*lonm.sum(), 'lat idx', np.where(latm)[0][[0,-1]], 'lon idx', np.where(lonm)[0][[0,-1]])
print('lat first/last:', lat[latm][0], lat[latm][-1], '| lon first/last:', lon[lonm][0], lon[lonm][-1])
