import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Load the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

# Define our region and time period
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
start_date = datetime(2021, 6, 1)
end_date = datetime(2021, 8, 31)

# Filter the region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"Region: lat [{lat_min}, {lat_max}], lon [{lon_min}, {lon_max}]")
print(f"Lat indices: {lat_indices[0]} to {lat_indices[-1]}")
print(f"Lon indices: {lon_indices[0]} to {lon_indices[-1]}")

# Filter the time period
time_mask = (ds.time >= np.datetime64(start_date)) & (ds.time <= np.datetime64(end_date))
time_indices = np.where(time_mask)[0]

print(f"Time period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print(f"Time indices: {time_indices[0]} to {time_indices[-1]}")

# Extract subset for analysis
subset = ds.isel(latitude=lat_indices, longitude=lon_indices, time=time_indices)
print(f"\nSubset shape: {subset.analysed_sst.shape}")

# Check if we have enough data for baseline period (1992-2002)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
baseline_mask = (ds.time >= np.datetime64(baseline_start)) & (ds.time <= np.datetime64(baseline_end))
baseline_indices = np.where(baseline_mask)[0]

print(f"\nBaseline period: {baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')}")
print(f"Baseline indices: {baseline_indices[0]} to {baseline_indices[-1]}")
print(f"Number of baseline days: {len(baseline_indices)}")