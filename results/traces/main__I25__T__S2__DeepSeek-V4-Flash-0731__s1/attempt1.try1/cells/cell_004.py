
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Get region indices
    lat_idx = np.where((ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77))[0]
    lon_idx = np.where((ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45))[0]
    
    # Load target period data (2016-06-01 to 2016-08-31)
    t_start = np.datetime64('2016-06-01')
    t_end = np.datetime64('2016-08-31')
    time_vals = ds.time.values
    t_mask = (time_vals >= t_start) & (time_vals <= t_end)
    t_idx = np.where(t_mask)[0]
    
    target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=slice(lat_idx[0], lat_idx[-1]), longitude=slice(lon_idx[0], lon_idx[-1])).values
    print("Target SST shape:", target_sst.shape)
    print("Target time range:", time_vals[t_idx[0]], "to", time_vals[t_idx[-1]])
    
    # Load baseline period data
    # We need 1991-12-27 to 2003-01-05 for the windows
    b_start = np.datetime64('1991-12-27')
    b_end = np.datetime64('2003-01-05')
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    
    baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=slice(lat_idx[0], lat_idx[-1]), longitude=slice(lon_idx[0], lon_idx[-1])).values
    baseline_time = time_vals[b_idx]
    print("Baseline SST shape:", baseline_sst.shape)
    print("Baseline time range:", baseline_time[0], "to", baseline_time[-1])
