import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Check if the file exists
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
try:
    file_exists = fs.exists(file_path)
    print(f"File exists: {file_exists}")
    
    if file_exists:
        # Open the dataset
        with fs.open(file_path, "rb") as f:
            ds = xr.open_dataset(f, engine="h5netcdf")
            print("Dataset opened successfully")
            print("Dimensions:", ds.dims)
            print("Variables:", list(ds.data_vars.keys()))
            print("Coordinates:")
            for coord in ds.coords:
                print(f"  {coord}: {ds[coord].shape}")
            
            # Print some info about SST variable
            if 'sst' in ds.data_vars:
                print("SST variable shape:", ds['sst'].shape)
                print("SST variable dims:", ds['sst'].dims)
                print("SST coordinates:")
                print("  lat:", ds['lat'][:5].values, "...")  # Show first 5 values
                print("  lon:", ds['lon'][:5].values, "...")  # Show first 5 values
                print("  time:", ds['time'][:5].values, "...")  # Show first 5 values
    else:
        print("File does not exist")
        
except Exception as e:
    print(f"Error accessing file: {e}")
