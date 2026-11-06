
import numpy as np
lat = np.arange(53.5, 66.0+0.02, 0.02)
# Actually let's get from the actual data
import xarray as xr
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values

lat_mask = (lat >= 57.85) & (lat <= 59.05)
lon_mask = (lon >= 21.01) & (lon <= 22.21)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat values in region:", lat[lat_idx])
print("lon values in region:", lon[lon_idx])
print("Num lat:", len(lat_idx), "Num lon:", len(lon_idx))
