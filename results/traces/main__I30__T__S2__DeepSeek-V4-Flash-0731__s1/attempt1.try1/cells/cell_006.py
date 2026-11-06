
import fsspec
import xarray as xr
import numpy as np
import pandas as pd
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    time = ds.time.values
    
    # Target period
    target_start = np.datetime64('2010-06-01')
    target_end = np.datetime64('2010-08-31')
    target_mask = (time >= target_start) & (time <= target_end)
    target_idx = np.where(target_mask)[0]
    print("Target indices:", target_idx[0], "to", target_idx[-1], "count:", len(target_idx))
    print("Target dates:", time[target_idx[0]], "to", time[target_idx[-1]])
    
    # Baseline period with window extension
    # Baseline 1992-01-01 to 2002-12-31, plus windows: 1991-12-27 to 1991-12-31, 2003-01-01 to 2003-01-05
    base_start = np.datetime64('1991-12-27')
    base_end = np.datetime64('2003-01-05')
    base_mask = (time >= base_start) & (time <= base_end)
    base_idx = np.where(base_mask)[0]
    print("Baseline indices:", base_idx[0], "to", base_idx[-1], "count:", len(base_idx))
    print("Baseline dates:", time[base_idx[0]], "to", time[base_idx[-1]])
