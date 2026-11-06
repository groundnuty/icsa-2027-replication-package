
code = r'''
import numpy as np, xarray as xr, time, pandas as pd
t0=time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
la=ds.latitude.values; lo=ds.longitude.values
m_la=(la>=56.13-1e-6)&(la<=57.33+1e-6); m_lo=(lo>=17.71-1e-6)&(lo<=18.91+1e-6)
li=np.where(m_la)[0]; oi=np.where(m_lo)[0]
sub = ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(oi[0],oi[-1]+1))
tb = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tt = sub.sel(time=slice('2015-06-01','2015-08-31')).load()
print(time.time()-t0, tb.shape, tt.shape)
A=tb.values.astype(np.float64); T=tt.values.astype(np.float64)
print('finite frac base', np.isfinite(A).mean(), 'target', np.isfinite(T).mean())
sea = np.all(np.isfinite(T),axis=0)
print('sea cells', sea.sum(), sea.size, 'cells finite all baseline', np.isfinite(A).all(axis=0).sum())
print(tt.latitude.values[[0,-1]], tt.longitude.values[[0,-1]], tt.time.values[[0,-1]], np.nanmin(T), np.nanmax(T))
print('nt target', T.shape[0], 'baseline dates', tb.time.values[[0,-1]])
'''
open('/work/a.py','w').write(code)
import subprocess
r=subprocess.run(['python','/work/a.py'],capture_output=True,text=True); print(r.stdout[-4000:], r.stderr[-3000:])
