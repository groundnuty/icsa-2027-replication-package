import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Define our region boundaries
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

# Filter to our region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define our target period
start_date = datetime(2017, 6, 1)
end_date = datetime(2017, 8, 31)

# Filter to our time period
ds_period = ds_region.sel(time=slice(start_date, end_date))

# Get the actual SST data
sst_data = ds_period.analysed_sst.values  # Shape: (92, 60, 60)
print(f"SST data shape: {sst_data.shape}")

# Now let's create a function to compute day-of-year for a datetime object
def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    return date.timetuple().tm_yday

# Create the baseline period (1992-01-01 to 2002-12-31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Generate all baseline dates
baseline_dates = []
current = baseline_start
while current <= baseline_end:
    baseline_dates.append(current)
    current += timedelta(days=1)

print(f"Baseline period: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Number of baseline days: {len(baseline_dates)}")

# Create a mapping from date to day-of-year for all baseline dates
date_to_doy_map = {date: date_to_doy(date) for date in baseline_dates}

# Now let's create a comprehensive approach to compute pools for each DOY
def get_pool_for_doy(target_doy, baseline_dates, date_to_doy_map):
    """
    Get all baseline dates that should contribute to the pool for a given day of year.
    """
    # For each date in baseline, if it matches the target DOY, include its window
    pool_dates = set()
    
    # Special handling for day 60 (February 29) - it's handled differently
    if target_doy == 60:
        # All Feb 29 dates from baseline should be included, plus their windows
        for date in baseline_dates:
            if date_to_doy_map[date] == 60:
                # Include dates within ±5 days of this date
                for i in range(-5, 6):
                    candidate_date = date + timedelta(days=i)
                    # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                    if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                        pool_dates.add(candidate_date)
    else:
        # For other DOYs, find all dates matching this DOY and include their windows
        for date in baseline_dates:
            if date_to_doy_map[date] == target_doy:
                # Include dates within ±5 days of this date
                for i in range(-5, 6):
                    candidate_date = date + timedelta(days=i)
                    # Ensure it's within valid range (1991-12-27 to 2003-01-05)
                    if datetime(1991, 12, 27) <= candidate_date <= datetime(2003, 1, 5):
                        pool_dates.add(candidate_date)
    
    return sorted(list(pool_dates))

# Let's also build a reverse mapping: from DOY to all dates with that DOY
doy_to_dates = {}
for date in baseline_dates:
    doy = date_to_doy_map[date]
    if doy not in doy_to_dates:
        doy_to_dates[doy] = []
    doy_to_dates[doy].append(date)

print(f"DOY 1 has {len(doy_to_dates[1])} dates")
print(f"DOY 60 has {len(doy_to_dates[60])} dates (Feb 29)")
print(f"DOY 61 has {len(doy_to_dates[61])} dates")

# Test getting a pool for a specific DOY
test_doy = 61
pool_dates = get_pool_for_doy(test_doy, baseline_dates, date_to_doy_map)
print(f"Pool dates for DOY {test_doy}: {len(pool_dates)} dates")
print(f"First few pool dates: {pool_dates[:5]}")
print(f"Last few pool dates: {pool_dates[-5:]}")