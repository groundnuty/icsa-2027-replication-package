import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open the file to examine its structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", dict(ds.dims))
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:", list(ds.coords.keys()))
    
    # Check the actual variable name and its properties
    if 'analysed_sst' in ds.data_vars:
        sst_var = ds['analysed_sst']
        print("\nAnalysed SST variable details:")
        print("Shape:", sst_var.shape)
        print("Dimensions:", sst_var.dims)
        print("Coordinates:", sst_var.coords)
        
        # Check some sample values
        print("\nSample SST values (first few elements):")
        print(sst_var.values.flat[:10])
        
        # Check coordinate ranges
        print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
        print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
        
        # Check time
        print("\nTime coordinate:", ds.time.values)