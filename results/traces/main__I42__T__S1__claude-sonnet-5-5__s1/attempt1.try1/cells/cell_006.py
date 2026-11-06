import fsspec,xarray as xr,numpy as np,pandas as pd,os,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('output',exist_ok=True)
def load(t):
    for k in range(4):
        try:
            with fs.open(f"{p}/sst_{t:%Y%m%d}.nc",'rb') as f:
                d=xr.open_dataset(f,engine='h5netcdf')
                d=d.sel(latitude=slice(62.2,63.5),longitude=slice(18.7,20.0)).load()
            return d
        except FileNotFoundError: return None
        except Exception as e: err=e; time.sleep(1)
    return ('err',str(err))
days=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2012-06-01','2012-08-31'))
t0=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,days))
print(time.time()-t0)
bad=[(d,r) for d,r in zip(days,res) if r is None or isinstance(r,tuple)]
print(len(bad),bad[:5])
import pickle
ok=[(d,r) for d,r in zip(days,res) if r is not None and not isinstance(r,tuple)]
d0=ok[0][1];print(d0.analysed_sst.dims,d0.latitude.values,d0.longitude.values)
pickle.dump(ok,open('/tmp/ok.pkl','wb'))