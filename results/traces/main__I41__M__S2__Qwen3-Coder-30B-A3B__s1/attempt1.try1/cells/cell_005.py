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

# Create a mask for the region
region_mask = np.zeros((len(ds.latitude), len(ds.longitude)), dtype=bool)
region_mask[np.ix_(lat_indices, lon_indices)] = True

# Get the time indices for our target period
time_indices = np.where((ds.time >= np.datetime64(start_date)) & 
                       (ds.time <= np.datetime64(end_date)))[0]

# Get the baseline time indices
baseline_indices = np.where((ds.time >= np.datetime64(baseline_start)) & 
                           (ds.time <= np.datetime64(baseline_end)))[0]

print(f"Region: lat {lat_min} to {lat_max}, lon {lon_min} to {lon_max}")
print(f"Target period: {start_date} to {end_date}")
print(f"Baseline period: {baseline_start} to {baseline_end}")
print(f"Number of time steps in target period: {len(time_indices)}")
print(f"Number of time steps in baseline period: {len(baseline_indices)}")

# Extract the SST data for the region and target period
sst_data = ds.analysed_sst.isel(time=time_indices, latitude=lat_indices, longitude=lon_indices)
print(f"SST data shape: {sst_data.shape}")

# Convert to Kelvin (the data appears to be in Celsius based on typical SST datasets)
# But looking at the metadata, it says "decoded from int16 scale factor 0.01 offset 273.15"
# So we need to apply the conversion: SST(K) = SST(C) + 273.15
# However, the data might already be in Kelvin, let's check
print(f"Sample SST values (first few): {sst_data.values.flatten()[:5]}")

# For now, let's proceed with the algorithm implementation