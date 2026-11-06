import fsspec
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
fs.get(f'{base}/sst_20210601.nc', '/work/sst_20210601.nc')
import xarray as xr
ds = xr.open_dataset('/work/sst_20210601.nc', engine='h5netcdf')
print(ds)
ds.close()
