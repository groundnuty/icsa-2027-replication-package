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
    if 'sst' in ds.data_vars:
        sst_var = ds['sst']
        print("\nSST variable shape:", sst_var.shape)
        print("SST variable dims:", sst_var.dims)
        print("SST coordinates:")
        for coord in sst_var.coords:
            print(f"  {coord}: {sst_var.coords[coord].shape}")
            
    # Show some sample data
    print("\nSample latitudes:", ds.lat.values[:5])
    print("Sample longitudes:", ds.lon.values[:5])
    
except Exception as e:
    print(f"Error opening dataset: {e}")