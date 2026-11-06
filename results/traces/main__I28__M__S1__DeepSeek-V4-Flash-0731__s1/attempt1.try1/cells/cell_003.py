
import xarray as xr
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc', engine='h5netcdf')
print(ds['analysed_sst'].values.shape)
print(ds['latitude'].values[:5], ds['latitude'].values[-5:])
print(ds['longitude'].values[:5], ds['longitude'].values[-5:])
print(ds['analysed_sst'].values[0, 200:210, 300:310])
