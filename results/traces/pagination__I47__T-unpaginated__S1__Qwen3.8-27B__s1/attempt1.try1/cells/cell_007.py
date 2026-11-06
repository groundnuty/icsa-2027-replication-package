
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
ds = xarray.open_dataset(f, engine="h5netcdf")
print(ds)
print("---global attrs---")
print(ds.attrs)
ds.close()
