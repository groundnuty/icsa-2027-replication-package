import os, time, fsspec, xarray as xr, numpy as np
os.makedirs('/sandbox/work/cache', exist_ok=True)
with open('/sandbox/work/persist_test.txt','w') as f:
    f.write('hello')
print('wrote persistence test file')
fs = fsspec.filesystem('onedata')
base='/icsa2027_data_20261101T090944Z/s1z'
import shutil
local='/sandbox/work/cache/sst_20090601.nc'
t0=time.time()
if not os.path.exists(local):
    with fs.open(f'{base}/sst_20090601.nc','rb') as rf, open(local,'wb') as wf:
        shutil.copyfileobj(rf, wf, 1<<20)
print('download time', round(time.time()-t0,2), 'size', os.path.getsize(local))
t0=time.time()
ds=xr.open_dataset(local, engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
latmask=(lat>=59.93-1e-4)&(lat<=61.13+1e-4)
lonmask=(lon>=18.69-1e-4)&(lon<=19.89+1e-4)
sub=ds['analysed_sst'].isel(time=0)[latmask][:,lonmask].values.astype(np.float32)
print('open+slice time', round(time.time()-t0,3), sub.shape, np.isfinite(sub).mean())
t0=time.time()
ds2=xr.open_dataset(local, engine='h5netcdf')
sub2=ds2['analysed_sst'].isel(time=0)[latmask][:,lonmask].values
print('re-open time', round(time.time()-t0,3))
