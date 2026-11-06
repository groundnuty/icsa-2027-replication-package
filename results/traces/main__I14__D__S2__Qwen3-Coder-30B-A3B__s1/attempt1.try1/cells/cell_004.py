import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import netCDF4 as nc
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')

# Define the region
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

# Find indices for the region
lat_indices = np.where((ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max))[0]
lon_indices = np.where((ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max))[0]

# Get the subset of data for our region
subset_ds = ds.sel(latitude=ds['latitude'][lat_indices], longitude=ds['longitude'][lon_indices])

print(f"Region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
print(f"Region dimensions: {subset_ds.dims}")
print(f"Number of latitude points: {len(lat_indices)}")
print(f"Number of longitude points: {len(lon_indices)}")

# Define target period
target_start = datetime(2015, 6, 1)
target_end = datetime(2015, 8, 31)

# Convert dates to time indices
time_values = ds['time'].values
target_start_idx = np.where(time_values >= np.datetime64(target_start))[0][0]
target_end_idx = np.where(time_values <= np.datetime64(target_end))[0][-1]

print(f"Target period: {target_start} to {target_end}")
print(f"Target time indices: {target_start_idx} to {target_end_idx}")

# Now we need to get all data for the baseline period (1992-2002)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

baseline_start_idx = np.where(time_values >= np.datetime64(baseline_start))[0][0]
baseline_end_idx = np.where(time_values <= np.datetime64(baseline_end))[0][-1]

print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Baseline time indices: {baseline_start_idx} to {baseline_end_idx}")

# Extract the data we need
analysed_sst = subset_ds['analysed_sst'].values
print(f"Analysed SST shape: {analysed_sst.shape}")

# Let's first create a helper function to convert dates to day-of-year
def date_to_doy(date):
    """Convert a datetime object to day-of-year (1-366)"""
    # Handle leap year cases
    if date.month == 2 and date.day == 29:
        return 60  # Special case for Feb 29
    
    # Use datetime to calculate day of year
    doy = date.timetuple().tm_yday
    
    # Adjust for leap years (we need to handle 29 Feb specially)
    if date.year % 4 == 0 and date.year != 1900:
        # This is a leap year
        if date.month > 2:
            doy -= 1  # Feb 29 is included in the calculation, but we want to treat it separately
    else:
        # Not a leap year
        pass
    
    return doy

# Actually, let's make a cleaner approach for DOY conversion
def get_doy(dt):
    """Convert datetime to day-of-year (1-366)"""
    # Create a date object without time component
    d = dt.date()
    # Get the day of year
    doy = d.timetuple().tm_yday
    
    # Special handling for Feb 29 in leap years
    if dt.month == 2 and dt.day == 29:
        return 60
    elif dt.month > 2 and (dt.year % 4 == 0 and dt.year != 1900):
        # For leap years, adjust day numbers after Feb 29
        if doy > 59:  # After Feb 29
            doy -= 1
    
    return doy

# Create a mapping from time indices to day-of-year for baseline period
baseline_times = time_values[baseline_start_idx:baseline_end_idx+1]
baseline_doy = [get_doy(datetime.fromisoformat(str(t)[:10])) for t in baseline_times]
baseline_doy = np.array(baseline_doy)

# Create a mapping from time indices to day-of-year for target period
target_times = time_values[target_start_idx:target_end_idx+1]
target_doy = [get_doy(datetime.fromisoformat(str(t)[:10])) for t in target_times]
target_doy = np.array(target_doy)

print(f"Sample baseline DOY: {baseline_doy[:10]}")
print(f"Sample target DOY: {target_doy[:10]}")

# Now let's proceed with the algorithm implementation