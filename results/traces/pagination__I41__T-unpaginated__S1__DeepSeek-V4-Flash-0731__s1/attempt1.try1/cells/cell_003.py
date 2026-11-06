
import fsspec
import xarray as xr
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print(ds.sst.dims)
print(ds.sst.attrs)
print(ds.coords)
