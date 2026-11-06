
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds.analysed_sst.attrs)
print(ds.analysed_sst.values.shape)
print(ds.latitude.values[:5])
print(ds.latitude.values[-5:])
print(ds.longitude.values[:5])
print(ds.longitude.values[-5:])
# Check the region
lat = ds.latitude.values
lon = ds.longitude.values
import numpy as np
lat_idx = np.where((lat >= 61.57) & (lat <= 62.77))[0]
lon_idx = np.where((lon >= 20.17) & (lon <= 21.37))[0]
print("lat_idx:", lat_idx.min(), lat_idx.max(), len(lat_idx))
print("lon_idx:", lon_idx.min(), lon_idx.max(), len(lon_idx))
print("lat range:", lat[lat_idx.min()], lat[lat_idx.max()])
print("lon range:", lon[lon_idx.min()], lon[lon_idx.max()])
