import xarray as xr
import numpy as np

# Try to open a file from the correct path
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
print(f"Trying to open: {sample_file}")

try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Successfully opened dataset")
    print("Dataset structure:")
    print(ds)
    
    # Look for SST variable
    print("\nAvailable variables:")
    for var in ds.data_vars:
        print(f"  {var}: {ds[var].dims}")
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")
    import traceback
    traceback.print_exc()