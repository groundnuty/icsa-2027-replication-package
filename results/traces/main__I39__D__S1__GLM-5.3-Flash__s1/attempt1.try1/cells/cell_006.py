import fsspec, time
fs = fsspec.filesystem('onedata')
t0 = time.time()
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sample_19820101.nc')
print('downloaded in', time.time()-t0, 's')

import xarray as xr
ds = xr.open_dataset('/work/sample_19820101.nc', engine='h5netcdf')
print(ds)
print('---')
print('lat[:5]', ds['lat'].values[:5] if 'lat' in ds else None)
