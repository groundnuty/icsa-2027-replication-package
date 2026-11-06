import xarray as xr
import numpy as np

# Try to open the main file
try:
    ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine='h5netcdf')
    print("Dataset opened successfully")
    print("Dimensions:", ds.dims)
    print("Variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    
    # Check the structure of SST data
    if 'analysed_sst' in ds.data_vars:
        sst_var = ds['analysed_sst']
        print("\nSST variable shape:", sst_var.shape)
        print("SST variable dims:", sst_var.dims)
        
    # Show coordinate information
    print("\nLatitude coordinate info:")
    print("Shape:", ds.latitude.shape)
    print("Sample values:", ds.latitude.values[:5])
    print("Min/Max:", ds.latitude.min().values, "/", ds.latitude.max().values)
    
    print("\nLongitude coordinate info:")
    print("Shape:", ds.longitude.shape)
    print("Sample values:", ds.longitude.values[:5])
    print("Min/Max:", ds.longitude.min().values, "/", ds.longitude.max().values)
    
    print("\nTime coordinate info:")
    print("Shape:", ds.time.shape)
    print("Sample values:", ds.time.values[:5])
    print("Min/Max:", ds.time.min().values, "/", ds.time.max().values)
    
except Exception as e:
    print(f"Error opening dataset: {e}")
    import traceback
    traceback.print_exc()