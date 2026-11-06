
import xarray as xr, fsspec
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

print(ds.time.values[:5])
print(ds.time.values[-5:])
print(ds.latitude.values[:5], ds.latitude.values[-5:])
print(ds.longitude.values[:5], ds.longitude.values[-5:])
print(ds.analysed_sst.dtype)
