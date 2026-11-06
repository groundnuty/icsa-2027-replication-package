import xarray as xr
import numpy as np

# Let's look at one file to understand the structure
file_path = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20230101.nc"
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    
    # Print some info about the SST variable
    if 'sst' in ds.data_vars:
        sst_var = ds['sst']
        print("\nSST variable info:")
        print("Shape:", sst_var.shape)
        print("Dimensions:", sst_var.dims)
        print("Attributes:", sst_var.attrs)
        
        # Show coordinates
        print("\nLatitudes:", ds['lat'].values[:5], "...")  # First 5 values
        print("Longitudes:", ds['lon'].values[:5], "...")  # First 5 values
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")