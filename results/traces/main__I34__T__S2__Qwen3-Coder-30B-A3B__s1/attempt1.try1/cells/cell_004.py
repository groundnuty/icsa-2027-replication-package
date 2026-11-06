import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89

# Filter the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print("Region dimensions:", ds_region.dims)
print("Region latitude range:", ds_region.latitude.min().values, "to", ds_region.latitude.max().values)
print("Region longitude range:", ds_region.longitude.min().values, "to", ds_region.longitude.max().values)

# Define the target period
start_date = datetime(2007, 6, 1)
end_date = datetime(2007, 8, 31)

# Find indices for the target period
time_indices = np.where((ds.time >= start_date) & (ds.time <= end_date))[0]

# Extract data for the target period
ds_target = ds.isel(time=time_indices)

# Extract data for the region and target period
ds_region_target = ds_target.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print("Target period:", len(ds_region_target.time), "days")
print("Target time range:", ds_region_target.time.min().values, "to", ds_region_target.time.max().values)