
script = r'''
import fsspec, xarray as xr, numpy as np, os, datetime as dt, sys
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work/sub',exist_ok=True)
start=dt.date(1991,12,27); end=dt.date(2003,1,5)
days=[]
d=start
while d<=end: days.append(d); d+=dt.timedelta(days=1)
d=dt.date(2009,6,1)
while d<=dt.date(2009,8,31): days.append(d); d+=dt.timedelta(days=1)
# region indices from one file
def sub_one(d):
    out=f'/work/sub/{d:%Y%m%d}.npz'
    if os.path.exists(out): return 'skip'
    loc=f'/work/tmp_{d:%Y%m%d}.nc'
    fs.get(base+f'sst_{d:%Y%m%d}.nc', loc)
    with xr.open_dataset(loc, engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        la=np.where((lat>=56.09)&(lat<=57.29))[0]; lo=np.where((lon>=10.55)&(lon<=11.75))[0]
        a=ds.analysed_sst.isel(latitude=la,longitude=lo).values
        t=ds.time.values
        np.savez(out, sst=a.astype(np.float64) if False else a, lat=lat[la], lon=lon[lo], time=t.astype('datetime64[D]').astype(str))
    os.remove(loc)
    return 'ok'
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(sub_one, days))
print(collections.Counter(res) if False else len(res), res.count('ok'), res.count('skip'))
'''
open('/work/dl.py','w').write(script)
import subprocess
r=subprocess.run(['python','/work/dl.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-2000:], r.stderr[-3000:])