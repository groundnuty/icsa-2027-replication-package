import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
start_date = datetime(2010, 6, 1)
end_date = datetime(2010, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Find indices for our region
lat_indices = np.where((ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max))[0]
lon_indices = np.where((ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max))[0]

print(f"Region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
print(f"Latitude indices: {lat_indices[0]} to {lat_indices[-1]}")
print(f"Longitude indices: {lon_indices[0]} to {lon_indices[-1]}")

# Filter data for our region
subset_ds = ds.isel(latitude=lat_indices, longitude=lon_indices)

print(f"Subset dimensions: {subset_ds.dims}")

# Now let's find the time indices for our period
time_indices = np.where((subset_ds['time'] >= np.datetime64(start_date)) & 
                       (subset_ds['time'] <= np.datetime64(end_date)))[0]

print(f"Target time period: {len(time_indices)} days")

# Also check baseline period
baseline_indices = np.where((subset_ds['time'] >= np.datetime64(baseline_start)) & 
                           (subset_ds['time'] <= np.datetime64(baseline_end)))[0]

print(f"Baseline period: {len(baseline_indices)} days")

# Let's look at some sample data to confirm
print("\nSample SST data for first few days in our region:")
print(subset_ds['analysed_sst'][:3, :3, :3])  # First 3 days, first 3 lat/lon points