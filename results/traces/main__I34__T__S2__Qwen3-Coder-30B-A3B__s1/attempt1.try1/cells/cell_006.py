import fsspec
import xarray as xr
import numpy as np
from datetime import datetime

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Print time range
print("Full time range:", ds.time.min().values, "to", ds.time.max().values)
print("Total time steps:", len(ds.time))

# Define the region of interest
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89

# Get indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print("Region indices - Lat:", lat_indices[0], "to", lat_indices[-1])
print("Region indices - Lon:", lon_indices[0], "to", lon_indices[-1])

# Define the target period
start_date = np.datetime64('2007-06-01')
end_date = np.datetime64('2007-08-31')

# Get indices for the target period
time_indices = np.where((ds.time >= start_date) & (ds.time <= end_date))[0]

print("Target period indices:", time_indices[0], "to", time_indices[-1])
print("Number of target days:", len(time_indices))