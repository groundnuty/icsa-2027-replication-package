
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find indices for region
lats = ds.latitude.values
lons = ds.longitude.values

lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# Find indices within bounds
lat_idx = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_idx = np.where((lons >= lon_min) & (lons <= lon_max))[0]

print(f"Lat indices: {lat_idx[0]} to {lat_idx[-1]}, count: {len(lat_idx)}")
print(f"Lat values: {lats[lat_idx[0]]} to {lats[lat_idx[-1]]}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, count: {len(lon_idx)}")
print(f"Lon values: {lons[lon_idx[0]]} to {lons[lon_idx[-1]]}")

# Check all lat/lon values in range
print("\nAll lats in range:")
for i in lat_idx:
    print(f"  {i}: {lats[i]}")
print("\nAll lons in range:")
for i in lon_idx:
    print(f"  {i}: {lons[i]}")
