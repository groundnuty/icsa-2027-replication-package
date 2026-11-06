# Let me debug the path issue directly
import fsspec
import xarray as xr
import numpy as np
from datetime import datetime

fs = fsspec.filesystem('onedata')

# Correct path construction
base_path = "/icsa2027_data_20261101T090944Z/s1z"

# Test specific file loading
test_filename = "sst_19920101.nc"
full_path = f"{base_path}/{test_filename}"

print(f"Looking for file: {full_path}")
print(f"File exists: {fs.exists(full_path)}")

if fs.exists(full_path):
    try:
        with fs.open(full_path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            print("Successfully loaded test file")
            print(f"Shape: {ds.analysed_sst.shape}")
            print(f"Lat range: {ds.latitude.min().values} to {ds.latitude.max().values}")
            print(f"Lon range: {ds.longitude.min().values} to {ds.longitude.max().values}")
            
            # Now let's see what happens when we try to slice it
            lat_vals = ds.latitude.values
            lon_vals = ds.longitude.values
            
            # Our region boundaries
            lat_min, lat_max = 54.81, 56.01
            lon_min, lon_max = 19.61, 20.81
            
            # Find indices
            lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
            lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]
            
            print(f"Region indices: lat {len(lat_indices)}, lon {len(lon_indices)}")
            if len(lat_indices) > 0 and len(lon_indices) > 0:
                print(f"Lat range in region: {lat_vals[lat_indices[0]]} to {lat_vals[lat_indices[-1]]}")
                print(f"Lon range in region: {lon_vals[lon_indices[0]]} to {lon_vals[lon_indices[-1]]}")
                
    except Exception as e:
        print(f"Error loading test file: {e}")
else:
    print("File not found")

# Let's also test with the target period
target_filename = "sst_20070601.nc"
target_full_path = f"{base_path}/{target_filename}"
print(f"\nLooking for target file: {target_full_path}")
print(f"Target file exists: {fs.exists(target_full_path)}")