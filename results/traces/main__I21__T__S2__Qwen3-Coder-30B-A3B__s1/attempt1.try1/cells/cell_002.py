import fsspec
import xarray as xr
import numpy as np

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the file
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    # Load the dataset
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Print basic info about the dataset
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    
    # Check the actual data range
    print("\nLatitude range:", ds.latitude.min().values, "to", ds.latitude.max().values)
    print("Longitude range:", ds.longitude.min().values, "to", ds.longitude.max().values)
    print("Time range:", ds.time.min().values, "to", ds.time.max().values)
    
    # Check shape
    print("\nShape of analysed_sst:", ds.analysed_sst.shape)
    
    # Look at some sample data
    print("\nSample SST data:")
    print(ds.analysed_sst.isel(time=0, latitude=0, longitude=0))