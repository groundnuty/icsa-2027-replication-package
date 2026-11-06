
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find the region indices
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25

lat = ds.latitude.values
lon = ds.longitude.values

lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]

print(f"Lat range: {lat[lat_idx[0]]:.4f} to {lat[lat_idx[-1]]:.4f}, count: {len(lat_idx)}")
print(f"Lon range: {lon[lon_idx[0]]:.4f} to {lon[lon_idx[-1]]:.4f}, count: {len(lon_idx)}")

# Find time indices
time = ds.time.values
print(f"\nTime range: {time[0]} to {time[-1]}")
print(f"Time count: {len(time)}")
print(f"Time step: {time[1] - time[0]}")

# Find baseline time indices
import numpy as np
# Baseline: 1991-12-27 to 2003-01-05 (with window)
t_start_baseline = np.datetime64('1991-12-27')
t_end_baseline = np.datetime64('2003-01-05')
baseline_idx = np.where((time >= t_start_baseline) & (time <= t_end_baseline))[0]
print(f"\nBaseline indices: {baseline_idx[0]} to {baseline_idx[-1]}")
print(f"Baseline count: {len(baseline_idx)}")
print(f"Baseline first: {time[baseline_idx[0]]}, last: {time[baseline_idx[-1]]}")

# Find target time indices
t_start_target = np.datetime64('2012-06-01')
t_end_target = np.datetime64('2012-08-31')
target_idx = np.where((time >= t_start_target) & (time <= t_end_target))[0]
print(f"\nTarget indices: {target_idx[0]} to {target_idx[-1]}")
print(f"Target count: {len(target_idx)}")
print(f"Target first: {time[target_idx[0]]}, last: {time[target_idx[-1]]}")
