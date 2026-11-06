import xarray as xr
import fsspec
import numpy as np
from datetime import datetime
import re

fs = fsspec.filesystem('onedata')

# Check if there's any way to get the actual dataset metadata
try:
    # Try to get metadata for a sample file to understand the dataset better
    sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
    with fs.open(sample_file, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print("Sample file metadata:")
        print("Variables:", list(ds.data_vars.keys()))
        print("Coords:", list(ds.coords.keys()))
        print("Time dim:", ds.dims.get('time', 'Not found'))
        print("Lat dim:", ds.dims.get('latitude', 'Not found'))  
        print("Lon dim:", ds.dims.get('longitude', 'Not found'))
        
        # Check if there's metadata about the dataset
        print("\nDataset attributes:")
        for attr in dir(ds):
            if not attr.startswith('_'):
                try:
                    val = getattr(ds, attr)
                    if not callable(val):
                        print(f"{attr}: {val}")
                except:
                    pass
                    
except Exception as e:
    print(f"Error reading sample file: {e}")

# Check if there are any other datasets in the space
try:
    space_files = fs.ls('/')
    print("\nTop-level space files:")
    for f in space_files[:10]:
        print(f"  {f}")
except Exception as e:
    print(f"Error listing space: {e}")