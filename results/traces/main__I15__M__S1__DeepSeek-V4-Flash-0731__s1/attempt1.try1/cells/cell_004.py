import xarray as xr
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', engine='h5netcdf')
sst = ds['analysed_sst']
print(sst.values.shape)
print("Lat range:", ds.latitude.values.min(), ds.latitude.values.max())
print("Lon range:", ds.longitude.values.min(), ds.longitude.values.max())
print("Sample values:", sst.values[0, 100:105, 100:105])
print("NaN count:", sst.isnull().sum().values)
print("dtype:", sst.dtype)
