import xarray as xr
import numpy as np

# Try to open the dataset
try:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    print("Dataset opened successfully!")
    print(ds)
except Exception as e:
    print(f"Error opening dataset: {e}")
    
    # Let's try another way to see what's available
    print("\nTrying to explore the directory structure...")
    import os
    base_path = '/data/icsa2027_data_20261101T090944Z'
    if os.path.exists(base_path):
        print("Files in the base directory:")
        for f in os.listdir(base_path):
            print(f"  {f}")
        
        s2z_path = os.path.join(base_path, 's2z')
        if os.path.exists(s2z_path):
            print("\nFiles in s2z directory:")
            for f in os.listdir(s2z_path):
                print(f"  {f}")
    else:
        print("Base path doesn't exist")