import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Define the region of interest
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print("Selected region dimensions:")
print(f"Latitude range: {ds_region.latitude.min().values} to {ds_region.latitude.max().values}")
print(f"Longitude range: {ds_region.longitude.min().values} to {ds_region.longitude.max().values}")
print(f"Region shape: {ds_region.analysed_sst.shape}")

# Define target period
start_date = '2008-06-01'
end_date = '2008-08-31'

# Select the time period
ds_target = ds_region.sel(time=slice(start_date, end_date))
print(f"\nTarget period: {start_date} to {end_date}")
print(f"Target period shape: {ds_target.analysed_sst.shape}")

# Check some sample data
print(f"\nSample SST data (first few values):")
print(ds_target.analysed_sst.isel(time=0, latitude=0, longitude=0).values)