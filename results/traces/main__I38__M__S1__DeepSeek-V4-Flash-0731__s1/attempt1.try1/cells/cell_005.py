
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20030601.nc', engine='h5netcdf')

lats = ds.latitude.values
lons = ds.longitude.values

lat_indices = np.where((lats >= 60.49) & (lats <= 61.69))[0]
lon_indices = np.where((lons >= 17.25) & (lons <= 18.45))[0]

print("Lat indices:", lat_indices[0], "to", lat_indices[-1], "count:", len(lat_indices))
print("Lon indices:", lon_indices[0], "to", lon_indices[-1], "count:", len(lon_indices))
print("Lat values:", lats[lat_indices[0]], "to", lats[lat_indices[-1]])
print("Lon values:", lons[lon_indices[0]], "to", lons[lon_indices[-1]])
