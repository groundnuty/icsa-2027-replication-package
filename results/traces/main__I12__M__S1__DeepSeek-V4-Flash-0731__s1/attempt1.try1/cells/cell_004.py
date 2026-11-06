
import xarray as xr
import numpy as np

ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
print("Lat range:", lats[0], lats[-1], "step:", lats[1]-lats[0], "n:", len(lats))
print("Lon range:", lons[0], lons[-1], "step:", lons[1]-lons[0], "n:", len(lons))

# Region: lat 56.09 to 57.29, lon 10.55 to 11.75
lat_mask = (lats >= 56.09) & (lats <= 57.29)
lon_mask = (lons >= 10.55) & (lons <= 11.75)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("Lat values:", lats[lat_idx[0]], lats[lat_idx[-1]])
print("Lon values:", lons[lon_idx[0]], lons[lon_idx[-1]])
