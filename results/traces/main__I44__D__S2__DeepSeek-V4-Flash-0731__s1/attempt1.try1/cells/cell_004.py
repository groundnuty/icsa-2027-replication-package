
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find indices for the region
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values

lat_mask = (lat_vals >= lat_min) & (lat_vals <= lat_max)
lon_mask = (lon_vals >= lon_min) & (lon_vals <= lon_max)

print("Lat indices:", np.where(lat_mask)[0])
print("Lat values:", lat_vals[lat_mask])
print("Lon indices:", np.where(lon_mask)[0])
print("Lon values:", lon_vals[lon_mask])
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Num time steps:", len(ds.time))

# Check the time steps - are they daily?
times = ds.time.values
print("First 10 times:", times[:10])
print("Last 10 times:", times[-10:])

# Check differences
diffs = np.diff(times.astype('datetime64[D]').astype(int))
print("Time diff min/max:", diffs.min(), diffs.max())
