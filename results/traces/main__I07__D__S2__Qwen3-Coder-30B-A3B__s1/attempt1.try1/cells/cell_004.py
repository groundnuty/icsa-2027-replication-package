import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Setup filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# First let's get the full baseline dataset to ensure we have enough data
baseline_ds = ds.sel(time=slice(baseline_start, baseline_end))

# Now filter to our specific region
baseline_ds = baseline_ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Filter target period
region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
region_ds = region_ds.sel(time=slice(start_date, end_date))

print(f"Region dimensions: {region_ds.dims}")
print(f"Region shape: {region_ds['analysed_sst'].shape}")
print(f"Baseline shape: {baseline_ds['analysed_sst'].shape}")

# Function to convert date to day-of-year (1-366)
def date_to_doy(date):
    # Convert to datetime if it's a numpy datetime64
    if hasattr(date, 'astype'):
        date = date.astype('datetime64[s]').astype('datetime64[ms]').astype(datetime)
    # Get day of year (1-366)
    doy = date.timetuple().tm_yday
    # Handle leap year case where Feb 29 is included
    if date.month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        if doy >= 60:  # After Feb 29
            doy += 1
    return doy

# Test the function
test_date = datetime(2021, 2, 28)
print(f"Date {test_date} -> DOY: {date_to_doy(test_date)}")

test_date = datetime(2021, 3, 1)
print(f"Date {test_date} -> DOY: {date_to_doy(test_date)}")

test_date = datetime(2020, 2, 29)  # Leap year
print(f"Date {test_date} -> DOY: {date_to_doy(test_date)}")