import fsspec
import xarray as xr
import numpy as np
from datetime import datetime

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Define our region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Filter to our region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define our target period
start_date = datetime(2017, 6, 1)
end_date = datetime(2017, 8, 31)

# Filter to our time period
ds_period = ds_region.sel(time=slice(start_date, end_date))

print(f"Region dimensions: {ds_region.dims}")
print(f"Time period: {ds_period.time.min().values} to {ds_period.time.max().values}")
print(f"Number of time steps: {len(ds_period.time)}")

# Show some basic info about the data
print(f"Sample SST data shape: {ds_period.analysed_sst.shape}")
print(f"Latitude range: {ds_region.latitude.min().values} to {ds_region.latitude.max().values}")
print(f"Longitude range: {ds_region.longitude.min().values} to {ds_region.longitude.max().values}")