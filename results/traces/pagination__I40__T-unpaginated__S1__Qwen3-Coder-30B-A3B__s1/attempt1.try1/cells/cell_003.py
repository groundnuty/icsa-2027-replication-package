import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open one file to understand the structure
file_path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset dimensions:", ds.dims)
    print("Dataset variables:", list(ds.data_vars.keys()))
    print("Coordinates:")
    for coord in ds.coords:
        print(f"  {coord}: {ds[coord].shape}")
    print("\nSample SST data:")
    print(ds['sst'].isel(time=0).values[:5, :5])
    print("\nLatitudes:", ds['latitude'].values[:5])
    print("Longitudes:", ds['longitude'].values[:5])