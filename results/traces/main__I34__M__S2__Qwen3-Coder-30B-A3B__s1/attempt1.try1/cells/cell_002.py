import xarray as xr
import numpy as np
import os

# Check if we can open the file
file_path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
print(f"Checking if file exists: {os.path.exists(file_path)}")

# Let's also check the actual directory structure more carefully
print("Looking at the directory structure...")
try:
    # Try to see what's in the s2z directory
    s2z_dir = "/data/icsa2027_data_20261101T090944Z/s2z/"
    if os.path.exists(s2z_dir):
        files = os.listdir(s2z_dir)
        print(f"Files in s2z directory: {files[:10]}...")  # Show first 10
    else:
        print("s2z directory doesn't exist")
except Exception as e:
    print(f"Error accessing directory: {e}")

# Let's try to check the metadata using a different method
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Successfully opened dataset")
    print(ds)
    ds.close()
except Exception as e:
    print(f"Failed to open dataset: {e}")