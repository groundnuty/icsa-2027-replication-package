import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define the region boundaries (inclusive)
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Define the target period
start_date = datetime(2007, 6, 1)
end_date = datetime(2007, 8, 31)

# Filter the dataset for our region and time period
print("Filtering dataset for region and time period...")
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
print("Region dataset shape:", region_ds.analysed_sst.shape)

# Filter for the target period
target_ds = region_ds.sel(time=slice(start_date, end_date))
print("Target period dataset shape:", target_ds.analysed_sst.shape)

# Check the time dimension
print("Target time range:", target_ds.time.min().values, "to", target_ds.time.max().values)
print("Number of days:", len(target_ds.time))

# Get the actual time values
times = target_ds.time.values
print("First few times:", times[:5])
print("Last few times:", times[-5:])