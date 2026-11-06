
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat_idx = np.where((ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77))[0]
    lon_idx = np.where((ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45))[0]
    
    print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
    print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
    
    # Load target period data with correct inclusive slicing
    t_start = np.datetime64('2016-06-01')
    t_end = np.datetime64('2016-08-31')
    time_vals = ds.time.values
    t_mask = (time_vals >= t_start) & (time_vals <= t_end)
    t_idx = np.where(t_mask)[0]
    
    # Use .isel with lists
    target_sst = ds['analysed_sst'].isel(
        time=t_idx, 
        latitude=lat_idx, 
        longitude=lon_idx
    ).values
    print("Target SST shape:", target_sst.shape)
    
    # Baseline
    b_start = np.datetime64('1991-12-27')
    b_end = np.datetime64('2003-01-05')
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=b_idx, 
        latitude=lat_idx, 
        longitude=lon_idx
    ).values
    baseline_time = time_vals[b_idx]
    print("Baseline SST shape:", baseline_sst.shape)
    print("Baseline time range:", baseline_time[0], "to", baseline_time[-1])
    print("Target time range:", time_vals[t_idx[0]], "to", time_vals[t_idx[-1]])
