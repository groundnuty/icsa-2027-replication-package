code = r'''
import xarray as xr, numpy as np, os, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
names=set(os.listdir(d))
ds=xr.open_dataset(f'{d}/sst_19820101.nc',engine='h5netcdf')
lat=ds.latitude.values.astype(np.float64); lon=ds.longitude.values.astype(np.float64)
ii=np.where((lat>=54.17-1e-6)&(lat<=55.37+1e-6))[0]; jj=np.where((lon>=13.25-1e-6)&(lon<=14.45+1e-6))[0]
ds.close()
req=[]
t=dt.date(1991,12,27)
while t<=dt.date(2003,1,5): req.append(t); t+=dt.timedelta(1)
t=dt.date(2014,5,27)
while t<=dt.date(2014,8,31): req.append(t); t+=dt.timedelta(1)
def load(r):
    p=f"{d}/sst_{r:%Y%m%d}.nc"
    with xr.open_dataset(p,engine='h5netcdf') as x:
        return x.analysed_sst.values[0,ii[0]:ii[-1]+1,jj[0]:jj[-1]+1].astype(np.float64)
t0=time.time()
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load, req))
print('load',time.time()-t0)
S=np.stack(arrs)
dates=np.array([np.datetime64(r) for r in req])
np.savez('/tmp/data.npz', S=S, dates=dates, lat=lat[ii], lon=lon[jj], ii=ii, jj=jj)
print(S.shape, np.isnan(S).mean())
'''
open('/tmp/load.py','w').write(code)
import subprocess
r=subprocess.run("cd /tmp && python load.py",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])