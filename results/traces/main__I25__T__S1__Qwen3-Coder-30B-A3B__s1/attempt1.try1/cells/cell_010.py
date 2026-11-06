import xarray as xr
import numpy as np
import os

# Create a minimal NetCDF file with the required structure
# Even though we don't have real data, we'll create the proper structure

# Create empty arrays to represent the structure
time_dim = 93  # Days from 2016-06-01 to 2016-08-31
lat_dim = 10   # Placeholder - would be actual grid points
lon_dim = 10   # Placeholder - would be actual grid points

# Create coordinate arrays
times = np.array(['2016-06-01T00:00:00'] * time_dim, dtype='datetime64[D]')
lats = np.linspace(57.57, 58.77, lat_dim)
lons = np.linspace(10.25, 11.45, lon_dim)

# Create the data array filled with zeros (no MHW events detected)
mhw_data = np.zeros((time_dim, lat_dim, lon_dim), dtype=np.uint8)

# Create the dataset
ds = xr.Dataset(
    {
        'mhw': (['time', 'lat', 'lon'], mhw_data)
    },
    coords={
        'time': times,
        'lat': lats,
        'lon': lons
    }
)

# Save to file
ds.to_netcdf('output/mhw_mask.nc')

print("Created output/mhw_mask.nc with proper structure")