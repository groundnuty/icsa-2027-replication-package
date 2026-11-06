import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("Dataset opened successfully.")

# Print basic info about the dataset
print("\nDataset dimensions:")
print(ds.dims)
print("\nDataset variables:")
print(ds.data_vars)
print("\nDataset coordinates:")
print(ds.coords)

# Check what variables we have
print("\nVariables in dataset:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")
    
# Check coordinate ranges
if 'latitude' in ds.coords:
    print(f"\nLatitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
if 'longitude' in ds.coords:
    print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")
if 'time' in ds.coords:
    print(f"Time range: {ds.time.min().values} to {ds.time.max().values}")

# Define our region of interest
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# Filter to our region
print("\nFiltering to region...")
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print(f"Region dimensions: {ds_region.dims}")

# Define our target period
start_date = datetime(2004, 6, 1)
end_date = datetime(2004, 8, 31)

# Filter to target period
print("Filtering to target period...")
ds_period = ds_region.sel(time=slice(start_date, end_date))
print(f"Period dimensions: {ds_period.dims}")

# Get the SST data
sst_data = ds_period['analysed_sst']

print(f"\nSST data shape: {sst_data.shape}")
print(f"Time range in filtered data: {sst_data.time.min().values} to {sst_data.time.max().values}")

# Show first few time steps
print("\nFirst few time steps:")
print(sst_data.time.values[:5])

# Let's also look at some sample data points
print("\nSample SST values (first 3x3 grid points):")
sample_sst = sst_data.isel(time=0).values[:3, :3]
print(sample_sst)

# Check if we have any data
print(f"\nNumber of valid (non-NaN) SST values in first time step: {np.sum(np.isfinite(sample_sst))}")
print(f"Total number of grid points: {sample_sst.size}")