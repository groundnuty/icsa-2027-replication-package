import xarray as xr, numpy as np
# check lat/lon and region identical in a 2003 file
ds3 = xr.open_dataset('/work/nc/sst_20030105.nc', engine='h5netcdf')
lat3 = ds3['latitude'].values.astype('float64'); lon3 = ds3['longitude'].values.astype('float64')
ds1 = xr.open_dataset('/work/dl/sst_19920101.nc', engine='h5netcdf')
print('coords same 2003 vs 1992:', np.array_equal(ds3['latitude'].values, ds1['latitude'].values), np.array_equal(ds3['longitude'].values, ds1['longitude'].values))
lat = lat3; lon = lon3
latm = (lat >= 62.25-1e-9) & (lat <= 63.45+1e-9)
lonm = (lon >= 18.73-1e-9) & (lon <= 19.93+1e-9)
print('region cells:', latm.sum()*lonm.sum(), 'lat idx', np.where(latm)[0][[0,-1]], 'lon idx', np.where(lonm)[0][[0,-1]])
print('lat values first/last:', lat[latm][0], lat[latm][-1])
print('lon values first/last:', lon[lonm][0], lon[lonm][-1])
