import fsspec, os
fs = fsspec.filesystem('onedata')
os.makedirs('/work/data', exist_ok=True)
# download one file for inspection
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_20210601.nc', '/work/data/test_20210601.nc')
print('downloaded', os.path.getsize('/work/data/test_20210601.nc'))

import xarray as xr
ds = xr.open_dataset('/work/data/test_20210601.nc', engine='h5netcdf')
print(ds)
print('--- attrs ---')
for k, v in ds.attrs.items():
    print(k, ':', str(v)[:200])
