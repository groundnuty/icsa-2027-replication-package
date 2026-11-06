
import fsspec, os
fs = fsspec.filesystem('onedata')
print(fs.ls('icsa2027_data_20261101T090944Z/s2z', detail=False))
os.makedirs('/work', exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
