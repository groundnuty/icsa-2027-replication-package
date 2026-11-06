
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
ds = xarray.open_dataset(f, engine="h5netcdf")
print(ds)
for name, v in ds.variables.items():
    print(name, v.dims, v.dtype, "attrs:", dict(list(v.attrs.items())[:6]))
ds.close()
