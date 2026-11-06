import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')
# Check coordinate ranges
file_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat_range = (float(ds.latitude.min()), float(ds.latitude.max()))
    lon_range = (float(ds.longitude.min()), float(ds.longitude.max()))
    print(f"Latitude range: {lat_range}")
    print(f"Longitude range: {lon_range}")
    
    # Check if our target region is covered
    target_lat_min, target_lat_max = 57.85, 59.05
    target_lon_min, target_lon_max = 21.01, 22.21
    
    print(f"Target lat range: [{target_lat_min}, {target_lat_max}]")
    print(f"Target lon range: [{target_lon_min}, {target_lon_max}]")
    
    # Check if target region is fully covered
    lat_covered = (lat_range[0] <= target_lat_min) and (lat_range[1] >= target_lat_max)
    lon_covered = (lon_range[0] <= target_lon_min) and (lon_range[1] >= target_lon_max)
    print(f"Target region covered in latitude: {lat_covered}")
    print(f"Target region covered in longitude: {lon_covered}")