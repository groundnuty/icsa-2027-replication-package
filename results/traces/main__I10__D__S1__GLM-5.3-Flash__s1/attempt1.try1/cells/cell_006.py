import os, shutil, time
print('disk free:', shutil.disk_usage('/work'))
os.makedirs('/work/target', exist_ok=True)
os.makedirs('/work/baseline', exist_ok=True)
os.makedirs('/work/output', exist_ok=True)

import fsspec, numpy as np, xarray as xr, datetime as dt
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# grid indices (from sample)
ds0 = xr.open_dataset('/work/tmp/sample.nc', engine='h5netcdf')
lat = ds0['latitude'].values.astype(np.float64)
lon = ds0['longitude'].values.astype(np.float64)
ds0.close()
latm = (lat >= 55.67) & (lat <= 56.87)
lonm = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.flatnonzero(latm); lon_idx = np.flatnonzero(lonm)
np.save('/work/lat_idx.npy', lat_idx); np.save('/work/lon_idx.npy', lon_idx)
np.save('/work/lat_vals.npy', ds0_latvals if False else lat[lat_idx].astype(np.float32))
print('lat vals dtype float32 saved; n =', lat_idx.size, lon_idx.size)

# download speed test: 8 files spread over the needed range, parallel 8
from concurrent.futures import ThreadPoolExecutor
test_dates = ['19920101','19950715','19980115','20000229','20021231','19911227','20030105','20050601']
def dl(d):
    fs.get(f'{base}/sst_{d}.nc', f'/work/tmp/test_{d}.nc')
    return d
t0 = time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(dl, test_dates))
print('8 files in', round(time.time()-t0,2), 's ->', res)

# verify time coord + shape for these
for d in test_dates[:3] + ['20050601']:
    p = f'/work/tmp/test_{d}.nc'
    with xr.open_dataset(p, engine='h5netcdf') as ds:
        tv = ds['time'].values[0]
        arr = ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values
        print(d, 'time:', str(tv)[:10], 'shape:', arr.shape, 'finite frac:', round(np.isfinite(arr).mean(),4),
              'global shape:', ds['analysed_sst'].shape)
