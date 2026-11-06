script = r'''
import fsspec, os, datetime, numpy as np, xarray as xr
from concurrent.futures import ThreadPoolExecutor
base='icsa2027_data_20261101T090944Z/s1z'
def dr(a,b):
    d=a
    while d<=b:
        yield d; d+=datetime.timedelta(1)
need=list(dr(datetime.date(1991,12,27),datetime.date(2003,1,5)))+list(dr(datetime.date(2014,5,27),datetime.date(2014,9,5)))
os.makedirs('/work/sst',exist_ok=True)
def job(d):
    fs = fsspec.filesystem('onedata')
    p=f"/work/sst/sst_{d:%Y%m%d}.nc"
    if not os.path.exists(p):
        fs.get(f"{base}/sst_{d:%Y%m%d}.nc", p+'.part'); os.rename(p+'.part',p)
    return d
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(job, need))
print('done', len(res))
'''
open('/work/dl.py','w').write(script) if os.path.isdir('/work') else None
import os
os.makedirs('/work',exist_ok=True); open('/work/dl.py','w').write(script)
import subprocess, time
t=time.time()
r=subprocess.run(['python','/work/dl.py'],capture_output=True,text=True,timeout=3000)
print(r.stdout[-2000:], r.stderr[-2000:], time.time()-t)