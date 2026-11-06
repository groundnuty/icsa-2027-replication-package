import fsspec,xarray as xr,numpy as np,pandas as pd,time,os,pickle
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z/'
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2017-06-01','2017-08-31'))
def load(d):
    err=None
    for k in range(4):
        try:
            with fs.open(f"{D}sst_{d:%Y%m%d}.nc",'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895)).load()
            return (x.analysed_sst.values[0].astype('float32'),x.latitude.values,x.longitude.values)
        except FileNotFoundError: return None
        except Exception as e: err=e;time.sleep(1)
    return ('err',str(err))
t=time.time()
with ThreadPoolExecutor(32) as ex: res=list(ex.map(load,dates))
print(time.time()-t)
bad=[(d,r) for d,r in zip(dates,res) if r is None or isinstance(r,tuple) and r[0]=='err']
print(len(bad),bad[:5])
ok=[(d,r) for d,r in zip(dates,res) if r not in(None,) and not(r[0]=='err')]
pickle.dump((ok),open('/tmp/cache.pkl','wb'))
print(ok[0][1][0].shape,ok[0][1][1],ok[0][1][2])