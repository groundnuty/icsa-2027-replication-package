
script = r'''
import numpy as np, fsspec, xarray as xr, time, os
os.makedirs('/tmp/w',exist_ok=True)
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
v=ds.analysed_sst
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=64.39-1e-6)&(lat<=65.59+1e-6))[0]; lo=np.where((lon>=23.41-1e-6)&(lon<=24.61+1e-6))[0]
tm=ds.time.values
i0=np.searchsorted(tm,np.datetime64('1991-12-27')); i1=np.searchsorted(tm,np.datetime64('2003-01-05'),side='right')
t=time.time()
xb=v.isel(time=slice(i0,i1),latitude=la,longitude=lo).values.astype(np.float64)
tb=tm[i0:i1]
j0=np.searchsorted(tm,np.datetime64('2013-06-01')); j1=np.searchsorted(tm,np.datetime64('2013-08-31'),side='right')
xt=v.isel(time=slice(j0,j1),latitude=la,longitude=lo).values.astype(np.float64)
tt=tm[j0:j1]
np.savez('/tmp/w/cache.npz',xb=xb,tb=tb.astype('datetime64[D]').astype(np.int64),xt=xt,tt=tt.astype('datetime64[D]').astype(np.int64),lat=lat[la],lon=lon[lo])
print(time.time()-t, xb.shape, xt.shape, tt[0], tt[-1], len(tt))
'''
open('/tmp/w/load.py','w').write(script)
import subprocess
print(subprocess.run(['python','/tmp/w/load.py'],capture_output=True,text=True))
