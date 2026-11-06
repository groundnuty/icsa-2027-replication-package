import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'

# Open a sample file to understand the structure
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Find indices for our region of interest
    lat_min, lat_max = 55.67, 56.87
    lon_min, lon_max = 16.45, 17.65
    
    # Get the lat/lon coordinates
    lats = ds['latitude'].values
    lons = ds['longitude'].values
    
    # Find indices within our region
    lat_indices = np.where((lats >= lat_min) & (lats <= lat_max))[0]
    lon_indices = np.where((lons >= lon_min) & (lons <= lon_max))[0]
    
    print(f"Region of interest: lat {lat_min} to {lat_max}°N, lon {lon_min} to {lon_max}°E")
    print(f"Available latitudes: {lats[0]} to {lats[-1]}°N")
    print(f"Available longitudes: {lons[0]} to {lons[-1]}°E")
    print(f"Number of lat points in region: {len(lat_indices)}")
    print(f"Number of lon points in region: {len(lon_indices)}")
    
    # Show some sample coordinates in our region
    if len(lat_indices) > 0 and len(lon_indices) > 0:
        print(f"Sample latitudes in region: {lats[lat_indices[:5]]}")
        print(f"Sample longitudes in region: {lons[lon_indices[:5]]}")
        
    # Get the actual subset for our region
    subset_lat_indices = slice(lat_indices[0], lat_indices[-1] + 1)
    subset_lon_indices = slice(lon_indices[0], lon_indices[-1] + 1)
    
    print(f"Subset slice for lat: {subset_lat_indices}")
    print(f"Subset slice for lon: {subset_lon_indices}")