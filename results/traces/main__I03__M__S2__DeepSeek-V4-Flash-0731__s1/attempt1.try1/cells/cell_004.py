
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds['latitude'].values
lon = ds['longitude'].values

# find indices in region
lat_mask = (lat >= 54.17) & (lat <= 55.37)
lon_mask = (lon >= 13.25) & (lon <= 14.45)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat indices:", lat_idx, "values:", lat[lat_idx])
print("lon indices:", lon_idx, "values:", lon[lon_idx])
print("lat range:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon range:", lon[lon_idx[0]], lon[lon_idx[-1]])
