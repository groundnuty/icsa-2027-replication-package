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

# Define the region of interest
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89

# Get indices for the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

# Define the target period
start_date = np.datetime64('2007-06-01')
end_date = np.datetime64('2007-08-31')

# Get indices for the target period
time_indices = np.where((ds.time >= start_date) & (ds.time <= end_date))[0]

# Extract the subset
ds_subset = ds.isel(latitude=lat_indices, longitude=lon_indices, time=time_indices)

print("Subset dimensions:", ds_subset.dims)
print("Subset shape:", ds_subset.analysed_sst.shape)
print("Subset time range:", ds_subset.time.min().values, "to", ds_subset.time.max().values)
print("Subset lat range:", ds_subset.latitude.min().values, "to", ds_subset.latitude.max().values)
print("Subset lon range:", ds_subset.longitude.min().values, "to", ds_subset.longitude.max().values)