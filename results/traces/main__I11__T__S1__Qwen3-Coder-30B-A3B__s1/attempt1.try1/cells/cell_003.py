import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open a sample file to understand the structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nAnalysed SST variable shape:", ds['analysed_sst'].shape)
    print("Analysed SST variable dims:", ds['analysed_sst'].dims)
    
    # Check the actual data range
    sst_data = ds['analysed_sst']
    print("Sample SST data (first 5 values):", sst_data.isel(latitude=0, longitude=0).values)
    print("Min SST:", sst_data.min().values)
    print("Max SST:", sst_data.max().values)
    print("Mean SST:", sst_data.mean().values)
    
    # Check lat/lon ranges
    print("Latitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
    print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)