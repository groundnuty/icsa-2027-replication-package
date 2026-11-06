import fsspec
import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Correct path based on what we saw
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

# Download the file
fs.get(remote_path, local_path)

# Open the dataset
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define our region
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

# Select the region for all time
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

print("Region selected for baseline calculation:")
print(f"Latitude range: {lat_min} to {lat_max}")
print(f"Longitude range: {lon_min} to {lon_max}")
print(f"Shape of data: {ds_region.analysed_sst.shape}")

# Get the full time dimension to filter for baseline years
all_times = ds_region.time.values
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# Filter baseline data
baseline_mask = (all_times >= baseline_start) & (all_times <= baseline_end)
baseline_times = all_times[baseline_mask]

print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Number of baseline days: {len(baseline_times)}")

# Extract baseline data for our region
baseline_data = ds_region.analysed_sst.isel(time=baseline_mask)

print("Baseline data shape:", baseline_data.shape)
print("Baseline data statistics:")
print(f"Min SST: {np.nanmin(baseline_data.values):.2f} K")
print(f"Max SST: {np.nanmax(baseline_data.values):.2f} K")
print(f"Mean SST: {np.nanmean(baseline_data.values):.2f} K")
print(f"NaN count: {np.sum(np.isnan(baseline_data.values))}")

# Now let's create a function to convert dates to day-of-year numbers
def date_to_doy(date):
    """Convert datetime to day-of-year (1-366)"""
    # Handle leap years correctly
    if isinstance(date, np.datetime64):
        date = date.astype(datetime)
    doy = date.timetuple().tm_yday
    # Special handling for Feb 29
    if date.month > 2 and (date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0)):
        # This is a leap year and we're past Feb 29, so adjust
        if doy >= 60:  # Jan 31 is day 31, Feb 28 is day 59, Mar 1 is day 60
            doy -= 1
    return doy

# Test the function
test_date = datetime(2000, 2, 29)  # leap year
print(f"Day of year for {test_date.date()}: {date_to_doy(test_date)}")
test_date = datetime(2001, 2, 28)  # non-leap year
print(f"Day of year for {test_date.date()}: {date_to_doy(test_date)}")
test_date = datetime(2001, 3, 1)  # should be 61
print(f"Day of year for {test_date.date()}: {date_to_doy(test_date)}")