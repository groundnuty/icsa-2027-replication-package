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
    print("\nSample analysed_sst data:")
    print(ds['analysed_sst'].isel(time=0).values[:5, :5])
    print("\nLatitudes range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
    print("Longitudes range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
    
    # Check if we can get the full lat/lon arrays
    lat_vals = ds['latitude'].values
    lon_vals = ds['longitude'].values
    print(f"\nLatitude shape: {lat_vals.shape}, sample values: {lat_vals[:5]}")
    print(f"Longitude shape: {lon_vals.shape}, sample values: {lon_vals[:5]}")