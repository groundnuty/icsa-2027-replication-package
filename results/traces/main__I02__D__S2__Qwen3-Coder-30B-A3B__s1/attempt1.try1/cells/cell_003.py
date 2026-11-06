import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Setup the filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Attempting to download file...")
try:
    fs.get(remote_path, local_path)
    print("Download completed.")
except Exception as e:
    print(f"Error downloading file: {e}")
    # Let's try to list available paths instead
    print("Available paths in root:")
    try:
        paths = fs.ls('/')
        print(paths)
    except Exception as e2:
        print(f"Error listing paths: {e2}")
        
    # Try to see what's in the space
    try:
        space_paths = fs.ls('/icsa2027_data_20261101T090944Z')
        print("Paths in space:")
        print(space_paths)
    except Exception as e3:
        print(f"Error accessing space: {e3}")