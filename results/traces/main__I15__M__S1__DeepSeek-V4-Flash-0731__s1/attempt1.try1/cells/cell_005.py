import xarray as xr
import numpy as np

# Check which indices in the grid fall within the region
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values

# Region: lat 56.13-57.33, lon 17.71-18.91
lat_mask = (lats >= 56.13) & (lats <= 57.33)
lon_mask = (lons >= 17.71) & (lons <= 18.91)

print("Lat indices:", np.where(lat_mask)[0])
print("Lat values:", lats[lat_mask])
print()
print("Lon indices:", np.where(lon_mask)[0])
print("Lon values:", lons[lon_mask])
