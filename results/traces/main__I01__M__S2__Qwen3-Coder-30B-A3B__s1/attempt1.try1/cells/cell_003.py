import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')

print("Dataset coordinates:")
print(f"time: {ds.time.min()} to {ds.time.max()}")
print(f"latitude: {ds.latitude.min()} to {ds.latitude.max()}")
print(f"longitude: {ds.longitude.min()} to {ds.longitude.max()}")

print("\nData variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")

# Check the actual data range we need
print(f"\nActual data range:")
print(f"  Time: {ds.time.min().values} to {ds.time.max().values}")
print(f"  Latitude: {ds.latitude.min().values} to {ds.latitude.max().values}")
print(f"  Longitude: {ds.longitude.min().values} to {ds.longitude.max().values}")

# Define our region of interest
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87

print(f"\nOur region of interest:")
print(f"  Latitude: {lat_min} to {lat_max}")
print(f"  Longitude: {lon_min} to {lon_max}")

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"\nRegion indices:")
print(f"  Latitude indices: {lat_indices[0]} to {lat_indices[-1]}")
print(f"  Longitude indices: {lon_indices[0]} to {lon_indices[-1]}")

# Extract the subset for our analysis
subset = ds.isel(latitude=lat_indices, longitude=lon_indices)

print(f"\nSubset dimensions:")
print(f"  time: {len(subset.time)}")
print(f"  latitude: {len(subset.latitude)}")
print(f"  longitude: {len(subset.longitude)}")

# Check what we're working with
print(f"\nSample data:")
print(f"  SST shape: {subset.analysed_sst.shape}")
print(f"  Sample SST values: {subset.analysed_sst[0, 0, 0].values}")