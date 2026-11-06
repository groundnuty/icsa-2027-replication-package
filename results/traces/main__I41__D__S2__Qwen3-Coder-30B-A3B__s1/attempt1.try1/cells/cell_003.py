import fsspec
import xarray as xr
import numpy as np
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Correct path based on what we saw
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Attempting to download file...")
try:
    # Check if file exists first
    file_exists = fs.exists(remote_path)
    print(f"File exists: {file_exists}")
    
    if file_exists:
        fs.get(remote_path, local_path)
        print("Download complete.")
        
        # Open the dataset
        ds = xr.open_dataset(local_path, engine='h5netcdf')
        print("Dataset opened successfully.")
        print(ds)
        
        # Look at coordinates and variables
        print("\nCoordinates:")
        for coord in ds.coords:
            coord_vals = ds[coord].values
            print(f"  {coord}: shape={coord_vals.shape}, sample={coord_vals.flat[:5] if hasattr(coord_vals, 'flat') else 'N/A'}")
        
        print("\nVariables:")
        for var in ds.data_vars:
            print(f"  {var}: dims={ds[var].dims}, shape={ds[var].shape}")
            
    else:
        print("File does not exist at the specified path.")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()