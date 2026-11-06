
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Select region indices
    lat = ds.latitude.values
    lon = ds.longitude.values
    time = ds.time.values
    
    lat_idx = np.where((lat >= 58.69) & (lat <= 59.89))[0]
    lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
    
    # Baseline period indices
    base_start = np.datetime64('1991-12-27')
    base_end = np.datetime64('2003-01-05')
    base_mask = (time >= base_start) & (time <= base_end)
    base_idx = np.where(base_mask)[0]
    
    # Target period indices
    target_start = np.datetime64('2010-06-01')
    target_end = np.datetime64('2010-08-31')
    target_mask = (time >= target_start) & (time <= target_end)
    target_idx = np.where(target_mask)[0]
    
    # Load baseline data
    baseline_sst = ds['analysed_sst'].isel(time=base_idx, latitude=lat_idx, longitude=lon_idx).values
    print("Baseline shape:", baseline_sst.shape)
    print("Baseline dtype:", baseline_sst.dtype)
    print("Baseline min/max:", np.nanmin(baseline_sst), np.nanmax(baseline_sst))
    print("NaN count:", np.isnan(baseline_sst).sum())
