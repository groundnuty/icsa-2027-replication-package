import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
import numpy as np
print('lat dtype:', lat.dtype, 'lon dtype:', lon.dtype)
print('lat min/max:', lat.min(), lat.max(), 'n=', len(lat))
print('lon min/max:', lon.min(), lon.max(), 'n=', len(lon))
print('lat diffs unique:', np.unique(np.diff(lat))[:10])
print('lon diffs unique:', np.unique(np.diff(lon))[:10])
# check region bounds
print('lat values near 59.93-61.13:')
m = (lat >= 59.9) & (lat <= 61.2)
print(lat[m])
print('lon values near 18.69-19.89:')
n = (lon >= 18.66) & (lon <= 19.92)
print(lon[n])
print('var attrs:', ds['analysed_sst'].attrs)
