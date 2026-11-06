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
            return ('ok',x.analysed_sst.values[0],x.latitude.values,x.longitude.values)
        except FileNotFoundError: return ('missing',)
        except Exception as e: err=e;time.sleep(1)
    return ('err',str(err))
with ThreadPoolExecutor(32) as ex: res=list(ex.map(load,dates))
pickle.dump((dates,res),open('/tmp/cache.pkl','wb'))
from collections import Counter
print(Counter(r[0] for r in res)); print([ (d,r) for d,r in zip(dates,res) if r[0]!='ok'][:5])
r=res[0];print(r[1].shape,r[1].dtype,r[2][[0,-1]],r[3][[0,-1]])