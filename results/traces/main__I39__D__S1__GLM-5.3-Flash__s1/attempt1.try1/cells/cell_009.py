import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
# print values around the bounds
print('lat around 60.49:', lat[(lat>60.40)&(lat<60.60)])
print('lat around 61.69:', lat[(lat>61.60)&(lat<61.80)])
print('lon around 17.25:', lon[(lon>17.15)&(lon<17.35)])
print('lon around 18.45:', lon[(lon>18.35)&(lon<18.55)])
# check spacing
dlat = np.diff(lat.astype('float64'))
dlon = np.diff(lon.astype('float64'))
print('dlat unique:', np.unique(np.round(dlat,6)))
print('dlon unique:', np.unique(np.round(dlon,6)))
