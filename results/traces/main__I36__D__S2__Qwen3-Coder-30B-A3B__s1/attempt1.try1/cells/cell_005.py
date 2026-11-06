import xarray as xr
import numpy as np
import os

# Load the dataset
local_path = '/work/sst_s2.nc'
ds = xr.open_dataset(local_path, engine="h5netcdf")

print("Dataset shape:", ds.sizes)
print("Time dimension:", ds.sizes['time'])
print("Latitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)

# Check what variables we have
print("\nAvailable variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")

# Examine the SST variable structure more closely
sst = ds['analysed_sst']
print(f"\nSST variable shape: {sst.shape}")
print(f"SST variable dtype: {sst.dtype}")

# Check the time range
print(f"\nTime range: {ds.time.min().values} to {ds.time.max().values}")

# Define our region boundaries
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Find indices for our region
lat_indices = np.where((ds.latitude >= lat_min) & (ds.latitude <= lat_max))[0]
lon_indices = np.where((ds.longitude >= lon_min) & (ds.longitude <= lon_max))[0]

print(f"\nRegion boundaries:")
print(f"Lat: {lat_min} to {lat_max}")
print(f"Lon: {lon_min} to {lon_max}")
print(f"Lat indices: {lat_indices[:5]}... (total: {len(lat_indices)})")
print(f"Lon indices: {lon_indices[:5]}... (total: {len(lon_indices)})")

# Verify we have data for the region
if len(lat_indices) > 0 and len(lon_indices) > 0:
    print(f"\nRegion has {len(lat_indices)} latitude points and {len(lon_indices)} longitude points")
    print(f"Sample latitudes: {ds.latitude.isel(latitude=lat_indices[:5]).values}")
    print(f"Sample longitudes: {ds.longitude.isel(longitude=lon_indices[:5]).values}")
    
    # Extract the region data
    region_sst = sst.isel(latitude=lat_indices, longitude=lon_indices)
    print(f"Region SST shape: {region_sst.shape}")
    
    # Check a sample of the data
    print(f"Sample data from region: {region_sst.isel(time=0).values.flatten()[:5]}")
else:
    print("No data found in the specified region!")