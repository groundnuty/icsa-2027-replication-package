import fsspec,xarray as xr,pandas as pd,numpy as np,os,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/c',exist_ok=True)
dates=list(pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d'))+list(pd.date_range('2013-06-01','2013-08-31').strftime('%Y%m%d'))
def dl(d):
    t=f'/work/t_{d}.nc'
    if os.path.exists(t) or os.path.exists(f'/work/c/{d}.nc'):return
    for k in range(4):
        try: fs.get(f'{D}/sst_{d}.nc',t);return
        except Exception as e: time.sleep(1)
def proc(d):
    o=f'/work/c/{d}.nc';t=f'/work/t_{d}.nc'
    if os.path.exists(o):return
    x=xr.open_dataset(t,engine='h5netcdf')
    x=x.sel(latitude=slice(64.35,65.65),longitude=slice(23.35,24.65)).load()
    x.to_netcdf(o);x.close();os.remove(t)
t0=time.time()
with ThreadPoolExecutor(8) as ex: list(ex.map(dl,dates[:100]))
print(time.time()-t0)
for d in dates[:100]:proc(d)
print(time.time()-t0)