import fsspec,os,numpy as np,pandas as pd,xarray as xr,time,glob
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z'
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31'))
os.makedirs('/work/raw',exist_ok=True)
def dl(t):
    out=f'/work/raw/{t:%Y%m%d}.nc'
    if os.path.exists(out): return 1
    for k in range(4):
        try:
            fs.get(f'{d}/sst_{t:%Y%m%d}.nc',out+'.part');os.rename(out+'.part',out);return 1
        except Exception as e: err=e;time.sleep(1)
    return str(err)
t0=time.time()
with ThreadPoolExecutor(8) as ex: res=list(ex.map(dl,days[:200]))
print(time.time()-t0,[r for r in res if r!=1][:3])