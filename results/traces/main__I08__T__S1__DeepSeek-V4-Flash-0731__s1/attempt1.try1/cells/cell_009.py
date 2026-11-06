
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lats = ds.latitude.values
lons = ds.longitude.values

# Find all indices where lat in [54.81, 56.01]
lat_in = np.where((lats >= 54.81) & (lats <= 56.01))[0]
lon_in = np.where((lons >= 19.61) & (lons <= 20.81))[0]

print("Lat in region:", len(lat_in), lats[lat_in[0]], "to", lats[lat_in[-1]])
print("Lon in region:", len(lon_in), lons[lon_in[0]], "to", lons[lon_in[-1]])

# Check boundaries
print("\nLats around lower bound:", lats[64:68])
print("Lats around upper bound:", lats[123:127])
print("Lons around lower bound:", lons[529:533])
print("Lons around upper bound:", lons[588:592])
