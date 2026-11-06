import xarray as xr
import numpy as np

# Let's look at one file to understand the structure in detail
file_path = "/data/icsa2027_data_20230101.nc"
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Dataset dimensions:", dict(ds.dims))
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    
    # Print some info about the SST variable
    if 'analysed_sst' in ds.data_vars:
        sst_var = ds['analysed_sst']
        print("\nSST variable info:")
        print("Shape:", sst_var.shape)
        print("Dimensions:", sst_var.dims)
        print("Attributes:", sst_var.attrs)
        print("Sample data (first 5 values):", sst_var.values.flat[:5])
        
        # Show coordinates
        lat_vals = ds['latitude'].values
        lon_vals = ds['longitude'].values
        print("\nLatitude range:", lat_vals.min(), "to", lat_vals.max())
        print("Longitude range:", lon_vals.min(), "to", lon_vals.max())
        print("Latitude shape:", lat_vals.shape)
        print("Longitude shape:", lon_vals.shape)
        
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")