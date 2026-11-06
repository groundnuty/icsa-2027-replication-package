import xarray as xr
import numpy as np

# Let's examine a sample file to understand the structure
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20230601.nc"
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset structure:")
    print(ds)
    print("\nCoordinates:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    
    # Check the SST variable specifically
    if 'sst' in ds.data_vars:
        print("\nSST variable info:")
        print(ds['sst'])
        print(f"SST shape: {ds['sst'].shape}")
        print(f"SST dtype: {ds['sst'].dtype}")
        
        # Show some sample values
        print(f"Sample SST values (first few): {ds['sst'].isel(time=0, lat=0, lon=0).values}")
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")