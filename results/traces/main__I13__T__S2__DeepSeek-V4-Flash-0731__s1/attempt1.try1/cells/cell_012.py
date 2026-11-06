
import fsspec
import xarray as xr
import numpy as np
import datetime
import os

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Select the region
    region = ds.sel(latitude=slice(56.09, 57.29), longitude=slice(10.55, 11.75))
    times = region.time.values
    lat_vals = region.latitude.values
    lon_vals = region.longitude.values
    
    # Get extended baseline indices
    t_s = np.datetime64('1991-12-27')
    t_e = np.datetime64('2003-01-05')
    idx_s = np.searchsorted(times, t_s)
    idx_e = np.searchsorted(times, t_e, side='right') - 1
    
    # Load extended baseline SST
    sst_base = region.analysed_sst[idx_s:idx_e+1].values.astype(np.float64)
    base_times = times[idx_s:idx_e+1]
    print("Extended baseline SST shape:", sst_base.shape)
    print("Extended baseline dates:", base_times[0], "to", base_times[-1])
    
    # Get target period indices
    tgt_s = np.datetime64('2021-06-01')
    tgt_e = np.datetime64('2021-08-31')
    ti_s = np.searchsorted(times, tgt_s)
    ti_e = np.searchsorted(times, tgt_e, side='right') - 1
    
    # Load target SST
    sst_target = region.analysed_sst[ti_s:ti_e+1].values.astype(np.float64)
    target_times = times[ti_s:ti_e+1]
    print("Target SST shape:", sst_target.shape)
    print("Target dates:", target_times[0], "to", target_times[-1])
    
    print("Lat shape:", lat_vals.shape)
    print("Lon shape:", lon_vals.shape)
