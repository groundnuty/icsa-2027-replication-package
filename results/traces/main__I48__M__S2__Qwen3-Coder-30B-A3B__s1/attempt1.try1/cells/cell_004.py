import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define the region boundaries
lat_min, lat_max = 64.51, 65.71
lon_min, lon_max = 21.97, 23.17

# Select the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print(f"Selected region dimensions:")
print(f"  Time: {ds_region.sizes['time']}")
print(f"  Latitude: {ds_region.sizes['latitude']}")
print(f"  Longitude: {ds_region.sizes['longitude']}")

# Define the target period
start_date = datetime(2016, 6, 1)
end_date = datetime(2016, 8, 31)

# Filter time period
ds_target = ds_region.sel(time=slice(start_date, end_date))

print(f"\nTarget period dimensions:")
print(f"  Time: {ds_target.sizes['time']}")
print(f"  Latitude: {ds_target.sizes['latitude']}")
print(f"  Longitude: {ds_target.sizes['longitude']}")

# Get the actual time values
time_values = ds_target.time.values
print(f"\nActual time range: {time_values[0]} to {time_values[-1]}")

# Extract SST data for the target period
sst_data = ds_target.analysed_sst.values
print(f"SST data shape: {sst_data.shape}")
print(f"SST data type: {sst_data.dtype}")

# Let's see some sample values
print(f"Sample SST values (first few days):")
for i in range(min(3, len(sst_data))):
    print(f"Day {i}: min={np.nanmin(sst_data[i]):.2f}, max={np.nanmax(sst_data[i]):.2f}")