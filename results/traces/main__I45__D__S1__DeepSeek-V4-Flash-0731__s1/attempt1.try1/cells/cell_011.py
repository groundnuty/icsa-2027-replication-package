
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find grid indices for our region
lats = ds['latitude'].values
lons = ds['longitude'].values

print("Lat step:", lats[1] - lats[0])
print("Lon step:", lons[1] - lons[0])

# Region: lat 63.31-64.51, lon 21.31-22.51
lat_idx = np.where((lats >= 63.31) & (lats <= 64.51))[0]
lon_idx = np.where((lons >= 21.31) & (lons <= 22.51))[0]
print("Lat indices:", lat_idx[0], "to", lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], "to", lon_idx[-1], "count:", len(lon_idx))
print("Lat values:", lats[lat_idx[0]], "to", lats[lat_idx[-1]])
print("Lon values:", lons[lon_idx[0]], "to", lons[lon_idx[-1]])
ds.close()
