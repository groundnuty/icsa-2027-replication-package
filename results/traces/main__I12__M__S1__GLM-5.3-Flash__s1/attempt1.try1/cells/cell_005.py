import xarray as xr
import numpy as np
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds.latitude.values.astype('float64')
lon = ds.longitude.values.astype('float64')
latmin, latmax = 56.09, 57.29
lonmin, lonmax = 10.55, 11.75
latmask = (lat >= latmin) & (lat <= latmax)
lonmask = (lon >= lonmin) & (lon <= lonmax)
ilat = np.where(latmask)[0]
ilon = np.where(lonmask)[0]
print('lat idx', ilat[0], ilat[-1], 'n', len(ilat))
print('lat values first/last:', lat[ilat[0]], lat[ilat[-1]])
print('expected regular:', lat[ilat[0]] + 0.02*np.arange(len(ilat)) - lat[ilat])
print('lon idx', ilon[0], ilon[-1], 'n', len(ilon))
print('lon values first/last:', lon[ilon[0]], lon[ilon[-1]])
print('lon regularity:', np.round(lon[ilon] - (lon[ilon[0]] + 0.02*np.arange(len(ilon))), 9)[:10])
print('shape of region:', len(ilat), len(ilon))
