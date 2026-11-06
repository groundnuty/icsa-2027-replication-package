
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds['analysed_sst'].values.shape)
print(ds['analysed_sst'].values.flatten()[:20])
print(ds['latitude'].values[:10], ds['latitude'].values[-5:])
print(ds['longitude'].values[:10], ds['longitude'].values[-5:])
