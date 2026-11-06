
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Check exact lat/lon values in the region
    lat_idx = np.where((ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77))[0]
    lon_idx = np.where((ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45))[0]
    
    print("Lat values in region:")
    print(ds.latitude.values[lat_idx[0]:lat_idx[-1]+1])
    print("\nLon values in region:")
    print(ds.longitude.values[lon_idx[0]:lon_idx[-1]+1])
    
    # Check the region size
    print(f"\nRegion: {len(lat_idx)} lat x {len(lon_idx)} lon = {len(lat_idx)*len(lon_idx)} cells")
