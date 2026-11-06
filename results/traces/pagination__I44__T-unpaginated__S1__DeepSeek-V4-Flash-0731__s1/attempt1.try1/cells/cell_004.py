import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    
    # Region bounds
    lat_min, lat_max = 63.31, 64.51
    lon_min, lon_max = 21.31, 22.51
    
    # Find indices
    lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
    lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
    
    print(f"Lat range: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}, count={len(lat_idx)}")
    print(f"Lon range: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}, count={len(lon_idx)}")
    print(f"lat_idx: {lat_idx[0]} to {lat_idx[-1]}")
    print(f"lon_idx: {lon_idx[0]} to {lon_idx[-1]}")
    
    # Check the SST values in the region
    sst = ds['analysed_sst'].values[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1]
    print(f"SST shape: {sst.shape}")
    print(f"SST finite: {np.isfinite(sst).sum()}, total: {sst.size}")
    print(f"SST min: {np.nanmin(sst)}, max: {np.nanmax(sst)}")
    print(f"Land cells: {np.isnan(sst).sum()}")
    print(ds['analysed_sst'].dtype)
