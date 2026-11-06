import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("Dataset opened successfully.")

# Let's look at a larger region to make sure we're getting data
lat_min, lat_max = 53.0, 57.0
lon_min, lon_max = 12.0, 16.0

print(f"Looking at region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")

# Filter to our region
print("Filtering to region...")
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

# Check how much valid data we have
print("\nChecking data validity:")
for i in range(min(5, sst_data.shape[0])):  # Check first 5 days
    day_data = sst_data.isel(time=i)
    valid_count = np.sum(np.isfinite(day_data.values))
    total_count = day_data.size
    print(f"Day {i}: {valid_count}/{total_count} valid values ({valid_count/total_count*100:.1f}%)")

# Let's also check the exact coordinates to make sure they match what we want
print(f"\nActual latitude range in selection: {ds_region.latitude.min().values} to {ds_region.latitude.max().values}")
print(f"Actual longitude range in selection: {ds_region.longitude.min().values} to {ds_region.longitude.max().values}")

# Try even more precise coordinates
print("\nTrying exact coordinates matching requirements:")
lat_min_exact, lat_max_exact = 54.17, 55.37
lon_min_exact, lon_max_exact = 13.25, 14.45

ds_region_exact = ds.sel(latitude=slice(lat_min_exact, lat_max_exact), longitude=slice(lon_min_exact, lon_max_exact))
print(f"Exact region dimensions: {ds_region_exact.dims}")

# Filter to target period for exact region
ds_period_exact = ds_region_exact.sel(time=slice(start_date, end_date))
print(f"Exact period dimensions: {ds_period_exact.dims}")

sst_data_exact = ds_period_exact['analysed_sst']
print(f"Exact SST data shape: {sst_data_exact.shape}")

# Check data validity for exact region
print("\nChecking data validity in exact region:")
for i in range(min(5, sst_data_exact.shape[0])):
    day_data = sst_data_exact.isel(time=i)
    valid_count = np.sum(np.isfinite(day_data.values))
    total_count = day_data.size
    print(f"Day {i}: {valid_count}/{total_count} valid values ({valid_count/total_count*100:.1f}%)")