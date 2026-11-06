
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20140601.nc', engine='h5netcdf')

# Check latitude and longitude ranges
lat = ds.latitude.values
lon = ds.longitude.values
print(f"Latitude range: {lat.min()} to {lat.max()}, step ~{lat[1]-lat[0]}")
print(f"Longitude range: {lon.min()} to {lon.max()}, step ~{lon[1]-lon[0]}")
print(f"Num latitudes: {len(lat)}, num longitudes: {len(lon)}")

# Find indices for our region
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45

lat_mask = (lat >= lat_min) & (lat <= lat_max)
lon_mask = (lon >= lon_min) & (lon <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"\nLatitude indices for region: {lat_idx.min()} to {lat_idx.max()}")
print(f"Longitude indices for region: {lon_idx.min()} to {lon_idx.max()}")
print(f"Latitudes in region: {lat[lat_idx]}")
print(f"Longitudes in region: {lon[lon_idx]}")
