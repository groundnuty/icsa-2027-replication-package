import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
# Define the region of interest
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define the target period
start_date = '2009-06-01'
end_date = '2009-08-31'

# Select the time period
ds_period = ds_region.sel(time=slice(start_date, end_date))

print("Region dimensions:")
print(ds_region.dims)
print("\nSelected time period:")
print(ds_period.time.values[:5])  # Show first 5 dates
print("...")
print(ds_period.time.values[-5:])  # Show last 5 dates

# Check the shape of the data we're working with
print(f"\nShape of SST data for region and period: {ds_period.analysed_sst.shape}")