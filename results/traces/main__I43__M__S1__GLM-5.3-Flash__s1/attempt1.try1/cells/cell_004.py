import numpy as np, xarray as xr
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20170601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds['latitude'].values.astype('float64')
lon = ds['longitude'].values.astype('float64')
print('lat first/last/step:', lat[0], lat[-1], np.diff(lat)[:5], 'uniform:', np.allclose(np.diff(lat), 0.02, atol=1e-12))
print('lon first/last/step:', lon[0], lon[-1], np.diff(lon)[:5], 'uniform:', np.allclose(np.diff(lon), 0.02, atol=1e-12))
la_min, la_max, lo_min, lo_max = 62.25, 63.45, 18.73, 19.93
lat_sel = (lat >= la_min - 1e-9) & (lat <= la_max + 1e-9)
lon_sel = (lon >= lo_min - 1e-9) & (lon <= lo_max + 1e-9)
print('lat in range:', lat[lat_sel])
print('lon in range:', lon[lon_sel])
print('nlat', lat_sel.sum(), 'nlon', lon_sel.sum())
