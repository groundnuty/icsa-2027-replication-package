import xarray as xr
import numpy as np
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_19920601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
print('lat dtype', lat.dtype, 'first/last', lat[0], lat[-1], 'diff', np.diff(lat)[:3], 'unique diffs', np.unique(np.round(np.diff(lat),6))[:5])
print('lon dtype', lon.dtype, 'first/last', lon[0], lon[-1], 'diff', np.diff(lon)[:3])
print('nlat', len(lat), 'nlon', len(lon))
# check grid regularity
dlat = np.diff(lat); dlon = np.diff(lon)
print('lat diffs unique', np.unique(np.round(dlat, 8)))
print('lon diffs unique', np.unique(np.round(dlon, 8)))
# Region selection
latmin, latmax = 56.09, 57.29
lonmin, lonmax = 10.55, 11.75
# grid spacing ~0.02; check whether region bounds align with grid points
print('lat mod 0.02 near bounds:', (np.array([latmin, latmax]) - 53.5)/0.02)
print('lon mod 0.02 near bounds:', (np.array([lonmin, lonmax]) - 9.0)/0.02)
