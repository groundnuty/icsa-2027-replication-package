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

# Filter the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print("Region dimensions:", dict(ds_region.dims))
print("Region latitude range:", ds_region.latitude.min().values, "to", ds_region.latitude.max().values)
print("Region longitude range:", ds_region.longitude.min().values, "to", ds_region.longitude.max().values)

# Define the target period
start_date = np.datetime64('2007-06-01')
end_date = np.datetime64('2007-08-31')

# Filter the time period
ds_filtered = ds_region.where((ds_region.time >= start_date) & (ds_region.time <= end_date), drop=True)

print("Target period data shape:", ds_filtered.analysed_sst.shape)
print("Target time range:", ds_filtered.time.min().values, "to", ds_filtered.time.max().values)