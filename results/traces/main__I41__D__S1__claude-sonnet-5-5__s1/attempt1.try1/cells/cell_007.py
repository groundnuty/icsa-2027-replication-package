import fsspec,os,numpy as np,pandas as pd,xarray as xr,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z'
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31'))
os.makedirs('/work/r',exist_ok=True)
def job(t):
    out=f'/work/r/{t:%Y%m%d}.nc'
    if os.path.exists(out): return 1
    for k in range(4):
        try:
            tmp=f'/work/tmp_{t:%Y%m%d}.nc'
            fs.get(f'{d}/sst_{t:%Y%m%d}.nc',tmp)
            x=xr.open_dataset(tmp,engine='h5netcdf')
            x=x.sel(latitude=slice(61.55,62.79),longitude=slice(20.15,21.39)).load()
            x.to_netcdf(out);x.close();os.remove(tmp);return 1
        except Exception as e: err=e;time.sleep(1)
    return str(err)
t0=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(job,days))
print(time.time()-t0,[r for r in res if r!=1][:5],len(res))