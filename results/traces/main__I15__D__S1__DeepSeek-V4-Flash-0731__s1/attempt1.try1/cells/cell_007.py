
import fsspec
fs = fsspec.filesystem('onedata')
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sst_19820101.nc')
import xarray as xr
ds = xr.open_dataset('/work/sst_19820101.nc', engine='h5netcdf')
print(ds)
print(ds.variables)
