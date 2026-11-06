code=r'''
import xarray as xr, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
D="/data/icsa2027_data_20261101T090944Z/s1z"
ds=xr.open_dataset(D+"/sst_19820101.nc",engine="h5netcdf")
lat=ds.latitude.values.astype(float); lon=ds.longitude.values.astype(float)
li=np.where((lat>=57.33-1e-6)&(lat<=58.53+1e-6))[0]; lj=np.where((lon>=9.03-1e-6)&(lon<=10.23+1e-6))[0]
def load(dt):
    p=f"{D}/sst_{dt:%Y%m%d}.nc"
    with xr.open_dataset(p,engine="h5netcdf") as d:
        a=d.analysed_sst.isel(time=0).values[np.ix_(li,lj)].astype(np.float64)
        t=pd.Timestamp(d.time.values[0])
    assert t==dt, (t,dt)
    return a
dates=list(pd.date_range("1991-12-27","2003-01-05"))+list(pd.date_range("2012-06-01","2012-08-31"))
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,dates))
A=np.stack(arrs)
np.savez("/tmp/sub.npz",sst=A,dates=np.array([str(d.date()) for d in dates]),lat=lat[li],lon=lon[lj])
print(A.shape, np.isnan(A).mean(), lat[li][[0,-1]], lon[lj][[0,-1]])
'''
open("/tmp/load.py","w").write(code)
import subprocess
r=subprocess.run("cd /tmp && python load.py",shell=True,capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])