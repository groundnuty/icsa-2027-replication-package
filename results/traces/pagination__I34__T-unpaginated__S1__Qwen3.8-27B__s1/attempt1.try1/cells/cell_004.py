
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
path = "icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc"
f = fs.open(path, "rb")
ds = xarray.open_dataset(f, engine="h5netcdf")
print(ds)
print()
for v in ds.variables:
    print(v, ds[v].dtype, dict(ds[v].attrs))
ds.close()
