import fsspec,xarray as xr,numpy as np,datetime as dt,os,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
days=[dt.date(1991,12,27)+dt.timedelta(i) for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
days+=[dt.date(2019,6,1)+dt.timedelta(i) for i in range(92)]
def get(d):
    for k in range(4):
        try:
            with fs.open(f'{p}/sst_{d:%Y%m%d}.nc','rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(64.505,65.715),longitude=slice(21.965,23.175)).load()
            return x.analysed_sst.values[0],x.latitude.values,x.longitude.values,x.analysed_sst.dtype
        except FileNotFoundError: return None
        except Exception as e: err=e;time.sleep(1)
    return 'err'+str(err)
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,days))
print(time.time()-t,sum(r is None for r in res),[r for r in res if isinstance(r,str)][:3])
ok=[r for r in res if isinstance(r,tuple)]
print(ok[0][0].shape,ok[0][1][[0,-1]],ok[0][2][[0,-1]],ok[0][3])
miss=[d for d,r in zip(days,res) if r is None];print(miss[:10])
import pickle;pickle.dump((days,res),open('/tmp/r.pkl','wb'))