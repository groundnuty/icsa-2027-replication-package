import fsspec
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Define our region boundaries
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

# Load one file to determine grid indices for our region
file_path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Get lat/lon coordinates
    lat_vals = ds['latitude'].values
    lon_vals = ds['longitude'].values
    
    # Find indices for our region
    lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
    lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]
    
    print(f"Region lat indices: {lat_indices[0]} to {lat_indices[-1]}")
    print(f"Region lon indices: {lon_indices[0]} to {lon_indices[-1]}")
    print(f"Region shape: {len(lat_indices)} x {len(lon_indices)}")
    
    # Verify the region bounds
    print(f"Actual lat range in region: {lat_vals[lat_indices[0]]} to {lat_vals[lat_indices[-1]]}")
    print(f"Actual lon range in region: {lon_vals[lon_indices[0]]} to {lon_vals[lon_indices[-1]]}")
    
    # Close the dataset
    ds.close()