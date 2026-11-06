code = r'''
import xarray as xr, numpy as np, os, pandas as pd
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lj=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
ii=slice(li[0],li[-1]+1); jj=slice(lj[0],lj[-1]+1)
bdates=pd.date_range('1991-12-27','2003-01-05')
tdates=pd.date_range('2021-06-01','2021-08-31')
alld=bdates.append(tdates)
def load(x):
    p=f"{d}/sst_{x:%Y%m%d}.nc"
    with xr.open_dataset(p, engine='h5netcdf') as f:
        t=pd.Timestamp(f.time.values[0])
        a=f.analysed_sst.isel(time=0, latitude=ii, longitude=jj).values.astype(np.float64)
        la=f.latitude.values[li]; lo=f.longitude.values[lj]
    return t,a,la,lo
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load, alld))
bad=[(x,t) for x,(t,a,_,_) in zip(alld,res) if t!=x]
print('time mismatches',len(bad), bad[:3])
A=np.stack([a for t,a,_,_ in res]); print(A.shape, np.isnan(A).mean())
np.savez('/tmp/sst.npz', A=A, dates=np.array([str(x.date()) for x in alld]), lat=res[0][2], lon=res[0][3])
'''
open('/tmp/load.py','w').write(code)
import subprocess
r=subprocess.run("cd /tmp && python load.py", shell=True, capture_output=True, text=True); print(r.stdout, r.stderr[-3000:])