import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    
    # Examine SST variable in detail
    print("SST variable details:")
    sst_var = ds['analysed_sst']
    print(f"Shape: {sst_var.shape}")
    print(f"Dimensions: {sst_var.dims}")
    print(f"Coordinates: lat({len(ds['latitude'])}), lon({len(ds['longitude'])}), time({len(ds['time'])})")
    
    # Look at a small subset of data
    print("\nSample SST data (first few time steps):")
    print(sst_var.isel(time=range(5)).values)
    
    # Look at time range
    print(f"\nTime range: {ds['time'].min().values} to {ds['time'].max().values}")
    
    # Look at lat/lon ranges
    print(f"\nLatitude range: {ds['latitude'].min().values} to {ds['latitude'].max().values}")
    print(f"Longitude range: {ds['longitude'].min().values} to {ds['longitude'].max().values}")
    
    # Check the specific region we're interested in
    lat_min, lat_max = 56.63, 57.83
    lon_min, lon_max = 20.23, 21.43
    
    # Find indices for our region
    lat_indices = np.where((ds['latitude'] >= lat_min) & (ds['latitude'] <= lat_max))[0]
    lon_indices = np.where((ds['longitude'] >= lon_min) & (ds['longitude'] <= lon_max))[0]
    
    print(f"\nRegion indices - Lat: {lat_indices[0]} to {lat_indices[-1]}, Lon: {lon_indices[0]} to {lon_indices[-1]}")
    
    # Show sample data for our region
    if len(lat_indices) > 0 and len(lon_indices) > 0:
        sample_sst = sst_var.isel(latitude=lat_indices[0:5], longitude=lon_indices[0:5])
        print(f"\nSample SST for our region (first 5x5 grid points):")
        print(sample_sst.values)