script = r'''
import fsspec, os, numpy as np, xarray as xr, datetime as dt, json, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
start=dt.date(1991,12,27); end=dt.date(2003,1,5)
days=[]
x=start
while x<=end: days.append(x); x+=dt.timedelta(1)
x=dt.date(2019,6,1)
while x<=dt.date(2019,8,31): days.append(x); x+=dt.timedelta(1)
def work(d):
    tag=d.strftime('%Y%m%d'); loc=f'/work/c/{tag}.nc'
    out=f'/work/c/{tag}.npz'
    if os.path.exists(out): return tag,'cached'
    fs.get(f'{base}/sst_{tag}.nc', loc)
    ds=xr.open_dataset(loc,engine='h5netcdf')
    s=ds.analysed_sst.sel(latitude=slice(64.51,65.71),longitude=slice(21.97,23.17)).load()
    np.savez(out, sst=s.values.astype(np.float32)[0] if s.ndim==3 else s.values.astype(np.float32), lat=s.latitude.values, lon=s.longitude.values)
    ds.close(); os.remove(loc)
    return tag,'ok'
os.makedirs('/work/c',exist_ok=True)
t0=time.time()
with ThreadPoolExecutor(8) as ex:
    for i,(tag,st) in enumerate(ex.map(work, days)):
        if i%200==0: print(i,tag,st,time.time()-t0,flush=True)
print('DONE',len(days),time.time()-t0,flush=True)
'''
open('/work/extract.py','w').write(script)
import subprocess
p=subprocess.Popen('cd /work && nohup python extract.py > extract.log 2>&1 &',shell=True)
import time; time.sleep(60)
print(open('/work/extract.log').read()[-2000:]); print(len(os.listdir('/work/c')))