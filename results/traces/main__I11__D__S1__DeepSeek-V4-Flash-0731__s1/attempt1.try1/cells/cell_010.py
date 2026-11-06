
import xarray as xr
import numpy as np

# Get the s2z file metadata without loading data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find the region indices
lat = ds.latitude.values
lon = ds.longitude.values
print(f"Lat range: {lat.min()} to {lat.max()}, count: {len(lat)}")
print(f"Lon range: {lon.min()} to {lon.max()}, count: {len(lon)}")

# Region: lat 55.67 to 56.87, lon 16.45 to 17.65
lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat indices: {lat_idx[0]} to {lat_idx[-1]}, count: {len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, count: {len(lon_idx)}")
print(f"Lat values: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}")
print(f"Lon values: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}")

# Check time values
time = ds.time.values
print(f"Time: {time[0]} to {time[-1]}, count: {len(time)}")
