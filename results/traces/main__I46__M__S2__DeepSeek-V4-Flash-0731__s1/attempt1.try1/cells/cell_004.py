
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds.latitude.values
lon = ds.longitude.values

# Find indices where 64.39 <= lat <= 65.59
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

print("lat indices:", lat_idx[0], lat_idx[-1], "values:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon indices:", lon_idx[0], lon_idx[-1], "values:", lon[lon_idx[0]], lon[lon_idx[-1]])
print("n lat:", len(lat_idx), "n lon:", len(lon_idx))
