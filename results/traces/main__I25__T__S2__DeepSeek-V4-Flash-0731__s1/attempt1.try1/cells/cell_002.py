
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Check latitudes and longitudes
    print("Latitudes range:", ds.latitude.values.min(), ds.latitude.values.max())
    print("Longitudes range:", ds.longitude.values.min(), ds.longitude.values.max())
    
    # Find region indices
    lat_mask = (ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77)
    lon_mask = (ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45)
    
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    
    print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
    print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
    print("Lat values:", ds.latitude.values[lat_idx[0]], ds.latitude.values[lat_idx[-1]])
    print("Lon values:", ds.longitude.values[lon_idx[0]], ds.longitude.values[lon_idx[-1]])
    
    # Find time indices for target period
    t_start = np.datetime64('2016-06-01')
    t_end = np.datetime64('2016-08-31')
    time_vals = ds.time.values
    t_mask = (time_vals >= t_start) & (time_vals <= t_end)
    t_idx = np.where(t_mask)[0]
    print("Time indices:", t_idx[0], t_idx[-1], "count:", len(t_idx))
    print("Time values:", time_vals[t_idx[0]], time_vals[t_idx[-1]])
    
    # Check baseline years 1992-2002
    b_start = np.datetime64('1992-01-01')
    b_end = np.datetime64('2002-12-31')
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    print("Baseline time indices:", b_idx[0], b_idx[-1], "count:", len(b_idx))
    
    # Also check if we need 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05
    # Those would be for window edges near end of baseline
    # Actually the baseline period for the pool is 1992-01-01 to 2002-12-31
    # but windows near ends reach up to 5 days beyond
    # Let's check what dates are available
    print("First date:", time_vals[0])
    print("Last date:", time_vals[-1])
