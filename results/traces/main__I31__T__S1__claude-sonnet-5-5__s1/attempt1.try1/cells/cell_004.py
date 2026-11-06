import numpy as np,pandas as pd,time
from concurrent.futures import ThreadPoolExecutor
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2017-06-01','2017-08-31'))
def load(d):
    for k in range(4):
        try:
            with fs.open(f"{D}sst_{d:%Y%m%d}.nc",'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895)).load()
            return x
        except FileNotFoundError: return None
        except Exception as e: err=e;time.sleep(1)
    return ('err',str(err))
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,dates))
print(time.time()-t)
bad=[(d,r) for d,r in zip(dates,res) if r is None or isinstance(r,tuple)]
print(len(bad),bad[:5])