
import xarray as xr
import numpy as np

f = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20220601.nc'
ds = xr.open_dataset(f, engine='h5netcdf')

lats = ds.latitude.values
lons = ds.longitude.values

# Region: lat 54.81 to 56.01, lon 19.61 to 20.81 inclusive
lat_mask = (lats >= 54.81) & (lats <= 56.01)
lon_mask = (lons >= 19.61) & (lons <= 20.81)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print(f"Lat range in region: {lats[lat_idx[0]]} to {lats[lat_idx[-1]]}, count={len(lat_idx)}")
print(f"Lon range in region: {lons[lon_idx[0]]} to {lons[lon_idx[-1]]}, count={len(lon_idx)}")
print(f"All lats in region: {lats[lat_idx]}")
print(f"All lons in region: {lons[lon_idx]}")
