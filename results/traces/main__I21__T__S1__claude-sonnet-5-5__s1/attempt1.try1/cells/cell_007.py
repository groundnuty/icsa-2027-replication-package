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
t=time.time();x=get(dt.date(1995,1,1));print(time.time()-t,x.analysed_sst.shape,x.latitude.values[[0,-1]],x.longitude.values[[0,-1]],x.analysed_sst.dtype)