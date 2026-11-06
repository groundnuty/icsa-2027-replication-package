import xarray as xr
import fsspec
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')

# Test reading some data files
test_dates = [
    datetime(2013, 6, 1),
    datetime(2013, 6, 15),
    datetime(2013, 6, 30),
    datetime(2013, 7, 15),
    datetime(2013, 8, 15)
]

print("Testing data availability...")
for date in test_dates:
    file_path = f'/icsa2027_data_20261101T090944Z/s1z/sst_{date.strftime("%Y%m%d")}.nc'
    try:
        with fs.open(file_path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            print(f"{date.strftime('%Y-%m-%d')}: Available, shape={ds.analysed_sst.shape}")
            # Check a few values
            sst_vals = ds.analysed_sst.values
            print(f"  Sample values: {sst_vals.flat[:5]}")
            # Check if we have any finite values
            finite_count = np.sum(np.isfinite(sst_vals))
            total_count = sst_vals.size
            print(f"  Finite values: {finite_count}/{total_count} ({finite_count/total_count*100:.1f}%)")
    except Exception as e:
        print(f"{date.strftime('%Y-%m-%d')}: Error - {e}")

# Check coordinate ranges for a sample file
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(sample_file, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat_range = (float(ds.latitude.min()), float(ds.latitude.max()))
    lon_range = (float(ds.longitude.min()), float(ds.longitude.max()))
    print(f"\nCoordinate ranges:")
    print(f"Latitude: {lat_range}")
    print(f"Longitude: {lon_range}")
    
    # Check specific region
    target_lat_min, target_lat_max = 57.85, 59.05
    target_lon_min, target_lon_max = 21.01, 22.21
    
    # Find indices in the grid
    lat_indices = np.where((ds.latitude >= target_lat_min) & (ds.latitude <= target_lat_max))[0]
    lon_indices = np.where((ds.longitude >= target_lon_min) & (ds.longitude <= target_lon_max))[0]
    
    print(f"\nTarget region indices:")
    print(f"Lat indices: {lat_indices[:5]}... (count: {len(lat_indices)})")
    print(f"Lon indices: {lon_indices[:5]}... (count: {len(lon_indices)})")
    
    # Check if there are any finite values in the target region
    sst_data = ds.analysed_sst.values
    print(f"\nSample SST values in target region:")
    if len(lat_indices) > 0 and len(lon_indices) > 0:
        for i in range(min(3, len(lat_indices))):
            for j in range(min(3, len(lon_indices))):
                lat_idx = lat_indices[i]
                lon_idx = lon_indices[j]
                val = sst_data[lat_idx, lon_idx]
                print(f"  ({lat_idx}, {lon_idx}): {val}")