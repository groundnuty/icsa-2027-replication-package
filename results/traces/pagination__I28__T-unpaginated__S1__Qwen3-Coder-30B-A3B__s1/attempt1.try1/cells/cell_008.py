import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Examine the structure more carefully
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset structure:")
    print(f"Dimensions: {ds.dims}")
    print(f"Variables: {list(ds.data_vars.keys())}")
    print(f"Coordinates: {list(ds.coords.keys())}")
    
    # Print actual coordinate values to understand
    print(f"\nLatitude values (first 5): {ds.latitude.values[:5]}")
    print(f"Longitude values (first 5): {ds.longitude.values[:5]}")
    
    # Check the SST data
    print(f"\nSST data shape: {ds.analysed_sst.shape}")
    print(f"SST data type: {ds.analysed_sst.dtype}")
    
    # Extract values for a small region
    target_lat_min, target_lat_max = 57.85, 59.05
    target_lon_min, target_lon_max = 21.01, 22.21
    
    # Find indices properly
    lat_mask = (ds.latitude >= target_lat_min) & (ds.latitude <= target_lat_max)
    lon_mask = (ds.longitude >= target_lon_min) & (ds.longitude <= target_lon_max)
    
    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]
    
    print(f"\nTarget region indices:")
    print(f"Lat indices (first 10): {lat_indices[:10]} (count: {len(lat_indices)})")
    print(f"Lon indices (first 10): {lon_indices[:10]} (count: {len(lon_indices)})")
    
    # Check the actual SST data structure - it looks like it might have a time dimension
    sst_data = ds.analysed_sst.values
    print(f"\nSST data shape: {sst_data.shape}")
    
    # Let's examine what happens when we read one of the target files
    target_date = datetime(2013, 6, 1)
    file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{target_date.strftime("%Y%m%d")}.nc'
    print(f"\nAnalyzing target file {target_date.strftime('%Y-%m-%d')}:")
    try:
        with fs.open(file_path, 'rb') as f:
            ds_target = xr.open_dataset(f, engine='h5netcdf')
            print(f"Target dataset dims: {ds_target.dims}")
            print(f"Target SST shape: {ds_target.analysed_sst.shape}")
            
            # Try to extract a small region
            sst_values = ds_target.analysed_sst.values[0]  # Remove time dimension
            print(f"After removing time dim, shape: {sst_values.shape}")
            
            # Check a small region
            if len(lat_indices) > 0 and len(lon_indices) > 0:
                # Extract a small region to check if there are finite values
                region_sst = sst_values[np.ix_(lat_indices[:5], lon_indices[:5])]
                print(f"Sample region values (5x5):")
                print(region_sst)
                
                finite_count = np.sum(np.isfinite(region_sst))
                total_count = region_sst.size
                print(f"Finite values in sample region: {finite_count}/{total_count}")
                
    except Exception as e:
        print(f"Error reading target file: {e}")
        import traceback
        traceback.print_exc()