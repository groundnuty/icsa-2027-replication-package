
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040101.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values

# Region: lat 54.17-55.37, lon 13.25-14.45 (inclusive)
lat_mask = (lat >= 54.17) & (lat <= 55.37)
lon_mask = (lon >= 13.25) & (lon <= 14.45)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat indices: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")
print(f"Lat values: {lat[lat_idx]}")
print(f"Lon values: {lon[lon_idx]}")
