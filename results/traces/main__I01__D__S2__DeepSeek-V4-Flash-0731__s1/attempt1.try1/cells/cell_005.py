
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region indices
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= 54.13) & (lat_sel <= 55.33))[0]
lon_idx = np.where((lon_sel >= 14.67) & (lon_sel <= 15.87))[0]
print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))

# Time period we need: 1991-12-27 to 2003-01-05 (for baseline with windows) plus target 2008
# Let's find indices
time_vals = ds.time.values

# baseline full range with windows
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
t_idx_base = np.where((time_vals >= base_start) & (time_vals <= base_end))[0]
print("Baseline time indices:", t_idx_base[0], t_idx_base[-1], "count:", len(t_idx_base))

# Target
tgt_start = np.datetime64('2008-06-01')
tgt_end = np.datetime64('2008-08-31')
t_idx_tgt = np.where((time_vals >= tgt_start) & (time_vals <= tgt_end))[0]
print("Target time indices:", t_idx_tgt[0], t_idx_tgt[-1], "count:", len(t_idx_tgt))
