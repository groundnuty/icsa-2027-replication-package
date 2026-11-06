import xarray as xr
import fsspec
import numpy as np

# Create the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nAnalysed SST variable info:")
    print(ds['analysed_sst'])
    
    # Check the shape and some sample data
    print(f"\nShape of analysed_sst: {ds['analysed_sst'].shape}")
    print(f"Sample data (first few values): {ds['analysed_sst'].isel(time=0, latitude=0, longitude=0)}")