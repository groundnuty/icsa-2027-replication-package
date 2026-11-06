script = r'''
import fsspec, os, datetime as dt, numpy as np, xarray as xr
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/sub',exist_ok=True); os.makedirs('/work/raw',exist_ok=True)
d0=dt.date(1991,12,27); d1=dt.date(2004,8,31)
dates=[d0+dt.timedelta(i) for i in range((d1-d0).days+1)]
# skip 2003-01-06..2004-05-31 (not needed)
dates=[d for d in dates if d<=dt.date(2003,1,5) or d>=dt.date(2004,6,1)]
latmask=None
for d in dates:
    out=f'/work/sub/{d:%Y%m%d}.npz'
    if os.path.exists(out): continue
    raw=f'/work/raw/{d:%Y%m%d}.nc'
    fs.get(f'{base}/sst_{d:%Y%m%d}.nc', raw)
    with xr.open_dataset(raw, engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        ri=np.where((lat>=63.31)&(lat<=64.51))[0]; ci=np.where((lon>=21.31)&(lon<=22.51))[0]
        sst=ds.analysed_sst.isel(time=0, latitude=ri, longitude=ci).values.astype(np.float64)
        np.savez(out, sst=sst, lat=lat[ri], lon=lon[ci], date=f'{d:%Y-%m-%d}')
    os.remove(raw)
print('DONE', flush=True)
'''
open('/work/fetch.py','w').write(script)
import subprocess
p=subprocess.Popen('nohup python /work/fetch.py > /work/fetch.log 2>&1 &', shell=True)
import time; time.sleep(60)
print(os.popen('ls /work/sub | wc -l; cat /work/fetch.log').read())