import fsspec,xarray as xr,numpy as np,datetime as dt,time,pickle
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
def get(d):
    n=f"{p}/sst_{d:%Y%m%d}.nc"
    for k in range(4):
        try:
            with fs.open(n,'rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(57.329,58.531),longitude=slice(9.029,10.231)).load()
            return x
        except Exception as e: err=e;time.sleep(1)
    raise err
def rng(a,b):
    d=a;o=[]
    while d<=b:o.append(d);d+=dt.timedelta(1)
    return o
days=rng(dt.date(1991,12,27),dt.date(2003,1,5))+rng(dt.date(2021,6,1),dt.date(2021,8,31))
t=time.time()
with ThreadPoolExecutor(8) as ex: xs=list(ex.map(get,days))
print(time.time()-t)
miss=[d for d,x in zip(days,xs) if x is None]
A=np.concatenate([x.analysed_sst.values for x in xs]).astype(np.float64)
print(A.shape,np.nanmin(A),np.nanmax(A),np.isnan(A).mean())
pickle.dump((days,A,xs[0].latitude.values,xs[0].longitude.values),open('/tmp/d.pkl','wb'))