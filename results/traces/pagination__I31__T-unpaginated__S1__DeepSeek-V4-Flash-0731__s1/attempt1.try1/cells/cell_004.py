
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
print("lat range:", lat.min(), lat.max(), "n=", len(lat))
print("lon range:", lon.min(), lon.max(), "n=", len(lon))
print("lat step:", lat[1]-lat[0])
print("lon step:", lon[1]-lon[0])

# Region bounds
lat_mask = (lat >= 58.69) & (lat <= 59.89)
lon_mask = (lon >= 18.69) & (lon <= 19.89)
print("lat idx:", np.where(lat_mask)[0])
print("lon idx:", np.where(lon_mask)[0])
print("lat values:", lat[lat_mask])
print("lon values:", lon[lon_mask])
