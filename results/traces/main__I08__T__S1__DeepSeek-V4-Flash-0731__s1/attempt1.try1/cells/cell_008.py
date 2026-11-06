
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

# Open the s2 file
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Get lat and lon coordinates
lats = ds.latitude.values
lons = ds.longitude.values
print("Lat range:", lats.min(), lats.max(), "n=", len(lats))
print("Lon range:", lons.min(), lons.max(), "n=", len(lons))
print("Time range:", ds.time.values[0], ds.time.values[-1])

# Find indices for region: lat 54.81-56.01, lon 19.61-20.81
lat_idx = np.where((lats >= 54.81) & (lats <= 56.01))[0]
lon_idx = np.where((lons >= 19.61) & (lons <= 20.81))[0]
print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("Lat values:", lats[lat_idx[0]], lats[lat_idx[-1]])
print("Lon values:", lons[lon_idx[0]], lons[lon_idx[-1]])
