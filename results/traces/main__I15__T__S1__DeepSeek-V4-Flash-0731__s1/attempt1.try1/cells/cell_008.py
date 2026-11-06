import xarray as xr
import fsspec
import numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check region indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
print("Lat range:", lat_vals[0], lat_vals[-1])
print("Lon range:", lon_vals[0], lon_vals[-1])

print("\nLat values near 56.13-57.33:")
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lat_idx = np.where(lat_mask)[0]
print("lat indices:", lat_idx[:5], "...", lat_idx[-5:])
print("lat count:", len(lat_idx))
print("lat values:", lat_vals[lat_idx[0]], lat_vals[lat_idx[-1]])

print("\nLon values near 17.71-18.91:")
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lon_idx = np.where(lon_mask)[0]
print("lon indices:", lon_idx[:5], "...", lon_idx[-5:])
print("lon count:", len(lon_idx))
print("lon values:", lon_vals[lon_idx[0]], lon_vals[lon_idx[-1]])

# Find time indices for baseline and target periods
t_vals = ds.time.values
print("\nTime indices for baseline 1992-2002:")
baseline_mask = (t_vals >= np.datetime64('1992-01-01')) & (t_vals <= np.datetime64('2002-12-31'))
b_idx = np.where(baseline_mask)[0]
print("baseline time idx:", b_idx[0], b_idx[-1], "count:", len(b_idx))

print("\nTime indices for target 2019-06-01 to 2019-08-31:")
target_mask = (t_vals >= np.datetime64('2019-06-01')) & (t_vals <= np.datetime64('2019-08-31'))
t_idx = np.where(target_mask)[0]
print("target time idx:", t_idx[0], t_idx[-1], "count:", len(t_idx))
print("Target times:", t_vals[t_idx[0]], t_vals[t_idx[-1]])
