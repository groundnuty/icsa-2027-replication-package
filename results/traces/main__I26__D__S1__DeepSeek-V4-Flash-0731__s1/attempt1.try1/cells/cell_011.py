import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get lat and lon arrays
lats = ds.latitude.values
lons = ds.longitude.values

# Find indices for region: lat 57.83-59.03, lon 17.41-18.61
lat_mask = (lats >= 57.83) & (lats <= 59.03)
lon_mask = (lons >= 17.41) & (lons <= 18.61)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat indices:", lat_idx.min(), "-", lat_idx.max(), "count:", len(lat_idx))
print("lon indices:", lon_idx.min(), "-", lon_idx.max(), "count:", len(lon_idx))
print("Selected lats:", lats[lat_idx.min()], "to", lats[lat_idx.max()])
print("Selected lons:", lons[lon_idx.min()], "to", lons[lon_idx.max()])
