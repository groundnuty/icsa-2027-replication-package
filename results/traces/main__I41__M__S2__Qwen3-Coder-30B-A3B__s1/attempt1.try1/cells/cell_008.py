import os
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

os.makedirs('output', exist_ok=True)

# Define region and time period
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Select the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"Selected lat indices: {len(lat_indices)}, lon indices: {len(lon_indices)}")

# Get the time indices for our target period
time_indices = np.where((ds.time >= np.datetime64(start_date)) & 
                       (ds.time <= np.datetime64(end_date)))[0]

# Get the baseline time indices
baseline_indices = np.where((ds.time >= np.datetime64(baseline_start)) & 
                           (ds.time <= np.datetime64(baseline_end)))[0]

print(f"Time indices for target: {len(time_indices)}, baseline: {len(baseline_indices)}")

# Extract the SST data for the region and target period
sst_data = ds.analysed_sst.isel(time=time_indices, latitude=lat_indices, longitude=lon_indices)
print(f"SST data shape: {sst_data.shape}")

# Extract dates and debug their types
dates = ds.time[time_indices].values
baseline_dates = ds.time[baseline_indices].values

print(f"Type of first date in target: {type(dates[0])}")
print(f"First date in target: {dates[0]}")

print(f"Type of first date in baseline: {type(baseline_dates[0])}")
print(f"First date in baseline: {baseline_dates[0]}")

# Directly compute day of year without complex logic
def simple_doy(dt):
    # Handle numpy datetime64
    if isinstance(dt, np.datetime64):
        dt = dt.astype(datetime)
    # Handle datetime objects
    elif hasattr(dt, 'year'):
        pass  # Already datetime object
    # If it's an integer or other type, just return as is
    else:
        return dt
        
    return dt.timetuple().tm_yday

# Create DOY arrays properly
target_doy = []
for date in dates:
    doy = simple_doy(date)
    target_doy.append(doy)
target_doy = np.array(target_doy)

baseline_doy = []
for date in baseline_dates:
    doy = simple_doy(date)
    baseline_doy.append(doy)
baseline_doy = np.array(baseline_doy)

print(f"Target DOY range: {target_doy.min()} to {target_doy.max()}")
print(f"Baseline DOY range: {baseline_doy.min()} to {baseline_doy.max()}")