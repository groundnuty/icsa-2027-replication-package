import xarray as xr
import numpy as np

# Try to open the dataset
try:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    print("Dataset opened successfully")
    print(ds)
except Exception as e:
    print(f"Error opening dataset: {e}")
    
    # Let's try to find the correct path
    import os
    base_path = '/data/icsa2027_data_20261101T090944Z'
    if os.path.exists(base_path):
        print("Files in the directory:")
        for root, dirs, files in os.walk(base_path):
            for file in files[:5]:  # Show first 5 files
                print(f"  {os.path.join(root, file)}")
    else:
        print("Base path doesn't exist")