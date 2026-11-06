
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    times = ds.time.values
    # Find indices for baseline (1992-01-01 to 2002-12-31)
    t0 = np.datetime64('1992-01-01')
    t1 = np.datetime64('2002-12-31')
    base_start = np.searchsorted(times, t0)
    base_end = np.searchsorted(times, t1, side='right') - 1
    print("Baseline indices:", base_start, base_end)
    print("Baseline time:", times[base_start], times[base_end])
    
    # Target period
    t0t = np.datetime64('2021-06-01')
    t1t = np.datetime64('2021-08-31')
    tgt_start = np.searchsorted(times, t0t)
    tgt_end = np.searchsorted(times, t1t, side='right') - 1
    print("Target indices:", tgt_start, tgt_end)
    print("Target time:", times[tgt_start], times[tgt_end])
    
    # Check if there are gaps in time
    diffs = np.diff(times[base_start:base_end+1])
    unique_diffs = np.unique(diffs)
    print("Unique time diffs in baseline:", unique_diffs)
    
    # Also check windows: 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05
    t_win1_s = np.datetime64('1991-12-27')
    t_win1_e = np.datetime64('1991-12-31')
    t_win2_s = np.datetime64('2003-01-01')
    t_win2_e = np.datetime64('2003-01-05')
    
    # We need those for window days near ends
    print("Checking if 1991-12-27 to 1991-12-31 exist in data:")
    mask1 = (times >= t_win1_s) & (times <= t_win1_e)
    print("  Found:", times[mask1])
    print("Checking if 2003-01-01 to 2003-01-05 exist in data:")
    mask2 = (times >= t_win2_s) & (times <= t_win2_e)
    print("  Found:", times[mask2])
