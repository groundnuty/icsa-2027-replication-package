
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    times = ds.time.values
    
    # Full range needed: 1991-12-27 to 2003-01-05
    t_s = np.datetime64('1991-12-27')
    t_e = np.datetime64('2003-01-05')
    idx_s = np.searchsorted(times, t_s)
    idx_e = np.searchsorted(times, t_e, side='right') - 1
    print("Extended baseline indices:", idx_s, idx_e)
    print("Extended baseline time:", times[idx_s], times[idx_e])
    print("Number of days:", idx_e - idx_s + 1)
    
    # Also check the last day in the dataset
    print("Last time:", times[-1])
