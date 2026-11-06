import xarray as xr
import numpy as np

# Let's examine the structure of one file
file_path = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20230101.nc"
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Dataset structure:")
    print(ds)
    print("\nCoordinates:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    
    # Check if we have the right variables
    if 'sst' in ds.data_vars:
        print("\nSST variable shape:", ds.sst.shape)
        print("SST variable dims:", ds.sst.dims)
        print("SST coordinates:", ds.sst.coords)
        
    # Check the time dimension
    if 'time' in ds.coords:
        print("\nTime coordinate info:")
        print(ds.time)
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")