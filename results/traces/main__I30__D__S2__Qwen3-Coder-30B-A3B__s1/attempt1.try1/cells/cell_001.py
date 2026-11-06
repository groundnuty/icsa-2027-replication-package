import fsspec
import xarray as xr
import numpy as np

# Create filesystem
fs = fsspec.filesystem('onedata')

# Try to list the directory structure
try:
    print("Available directories/files:")
    print(fs.ls('/'))
except Exception as e:
    print(f"Error listing root: {e}")

# Let's try to see if we can access the specific file
try:
    remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
    print(f"Trying to access: {remote_path}")
    
    # Check if file exists
    if fs.exists(remote_path):
        print("File exists")
        # Try to get file info
        file_info = fs.info(remote_path)
        print(f"File size: {file_info['size']} bytes")
    else:
        print("File does not exist")
        
except Exception as e:
    print(f"Error accessing file: {e}")