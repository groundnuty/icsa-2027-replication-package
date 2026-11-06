
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Find the region indices
lat_min, lat_max = 60.09, 61.29
lon_min, lon_max = 20.01, 21.21

# Get lat/lon values
lats = ds.latitude.values
lons = ds.longitude.values

# Find indices within bounds (inclusive)
lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)

print("Lat range in data:", lats.min(), lats.max())
print("Lon range in data:", lons.min(), lons.max())
print("Lat mask count:", lat_mask.sum())
print("Lon mask count:", lon_mask.sum())
print("Lat indices:", np.where(lat_mask)[0])
print("Lon indices:", np.where(lon_mask)[0])

# Check time range
print("Time:", ds.time.values[0], "to", ds.time.values[-1])

# Target period
target_start = '2003-06-01'
target_end = '2003-08-31'
# Baseline
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'
