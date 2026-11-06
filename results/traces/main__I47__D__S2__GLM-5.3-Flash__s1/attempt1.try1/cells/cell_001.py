import os, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
remote = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local = '/work/sst_s2.nc'
if not os.path.exists(local):
    fs.get(remote, local)
print('size bytes:', os.path.getsize(local))

import xarray as xr
ds = xr.open_dataset(local, engine='h5netcdf')
print(ds)

t = ds['time'].values
print('n_time', len(t), t[0], t[-1])
d = np.diff(t).astype('timedelta64[h]').astype(np.int64)
print('diff hours uniq:', np.unique(d))

latn = [c for c in ds.coords if 'lat' in c.lower()]
lonn = [c for c in ds.coords if 'lon' in c.lower()]
print(latn, lonn)
la = ds[latn[0]].values; lo = ds[lonn[0]].values
print('lat', la[0], la[-1], 'dlat uniq', np.unique(np.round(np.diff(la), 6))[:5])
print('lon', lo[0], lo[-1], 'dlon uniq', np.unique(np.round(np.diff(lo), 6))[:5])
m = (la >= 64.3) & (la <= 65.7)
print('lat near region:', la[m])
m2 = (lo >= 23.3) & (lo <= 24.7)
print('lon near region:', lo[m2])

for v in ds.data_vars:
    print(v, ds[v].dims, ds[v].dtype, {k: str(val)[:80] for k, val in ds[v].attrs.items()})
