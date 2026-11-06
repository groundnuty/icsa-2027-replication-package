
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds['analysed_sst'])
print(ds['time'].values[:5], ds['time'].values[-5:])
print(len(ds['time']))
# Region
lat = ds['latitude'].values
lon = ds['longitude'].values
print("lat range", lat.min(), lat.max(), "n=", len(lat))
print("lon range", lon.min(), lon.max(), "n=", len(lon))

# Find indices for region
lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat_idx", lat_idx.min(), lat_idx.max(), "count", len(lat_idx))
print("lon_idx", lon_idx.min(), lon_idx.max(), "count", len(lon_idx))
print("lat vals", lat[lat_idx.min()], lat[lat_idx.max()])
print("lon vals", lon[lon_idx.min()], lon[lon_idx.max()])
