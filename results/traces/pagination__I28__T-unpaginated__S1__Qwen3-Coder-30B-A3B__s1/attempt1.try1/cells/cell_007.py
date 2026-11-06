import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Check coordinate ranges for a sample file
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat_range = (float(ds.latitude.min()), float(ds.latitude.max()))
    lon_range = (float(ds.longitude.min()), float(ds.longitude.max()))
    print(f"Coordinate ranges:")
    print(f"Latitude: {lat_range}")
    print(f"Longitude: {lon_range}")
    print(f"Latitude shape: {ds.latitude.shape}")
    print(f"Longitude shape: {ds.longitude.shape}")
    
    # Check specific region
    target_lat_min, target_lat_max = 57.85, 59.05
    target_lon_min, target_lon_max = 21.01, 22.21
    
    # Find indices in the grid
    lat_mask = (ds.latitude >= target_lat_min) & (ds.latitude <= target_lat_max)
    lon_mask = (ds.longitude >= target_lon_min) & (ds.longitude <= target_lon_max)
    
    lat_indices = np.where(lat_mask)[0]
    lon_indices = np.where(lon_mask)[0]
    
    print(f"\nTarget region indices:")
    print(f"Lat indices (first 10): {lat_indices[:10]} (count: {len(lat_indices)})")
    print(f"Lon indices (first 10): {lon_indices[:10]} (count: {len(lon_indices)})")
    
    # Check if there are any finite values in the target region for a specific day
    sst_data = ds.analysed_sst.values
    print(f"\nSample SST values in target region:")
    if len(lat_indices) > 0 and len(lon_indices) > 0:
        # Take first few indices to avoid memory issues
        for i in range(min(3, len(lat_indices))):
            for j in range(min(3, len(lon_indices))):
                lat_idx = lat_indices[i]
                lon_idx = lon_indices[j]
                val = sst_data[lat_idx, lon_idx]
                print(f"  ({lat_idx}, {lon_idx}): {val}")

# Test with one of the target dates to make sure data is readable
target_date = datetime(2013, 6, 1)
file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{target_date.strftime("%Y%m%d")}.nc'
print(f"\nAnalyzing {target_date.strftime('%Y-%m-%d')}:")

try:
    with fs.open(file_path, 'rb') as f:
        ds = xr.open_dataset(f, engine='h5netcdf')
        print(f"Shape: {ds.analysed_sst.shape}")
        
        # Try to extract a small subset of the data to analyze
        sst_values = ds.analysed_sst.values[0]  # Remove time dimension
        print(f"SST values shape: {sst_values.shape}")
        
        # Check how many finite values we have
        finite_count = np.sum(np.isfinite(sst_values))
        total_count = sst_values.size
        print(f"Finite values: {finite_count}/{total_count} ({finite_count/total_count*100:.1f}%)")
        
        # Look at the target region specifically
        lat_indices = np.where((ds.latitude >= target_lat_min) & (ds.latitude <= target_lat_max))[0]
        lon_indices = np.where((ds.longitude >= target_lon_min) & (ds.longitude <= target_lon_max))[0]
        
        print(f"Target region indices:")
        print(f"Lat indices: {lat_indices[:5]}... (count: {len(lat_indices)})")
        print(f"Lon indices: {lon_indices[:5]}... (count: {len(lon_indices)})")
        
        # Extract the target region
        if len(lat_indices) > 0 and len(lon_indices) > 0:
            region_sst = sst_values[np.ix_(lat_indices, lon_indices)]
            region_finite = np.sum(np.isfinite(region_sst))
            region_total = region_sst.size
            print(f"Target region finite values: {region_finite}/{region_total} ({region_finite/region_total*100:.1f}%)")
            
            # Show some values from the region
            print("Sample values from target region:")
            sample_lat_indices = lat_indices[:3]
            sample_lon_indices = lon_indices[:3]
            for i, lat_idx in enumerate(sample_lat_indices):
                for j, lon_idx in enumerate(sample_lon_indices):
                    val = region_sst[i, j]
                    print(f"  ({lat_idx}, {lon_idx}): {val}")
                    
except Exception as e:
    print(f"Error: {e}")