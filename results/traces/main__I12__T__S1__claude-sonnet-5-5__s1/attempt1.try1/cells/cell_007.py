import fsspec,xarray as xr,numpy as np,pandas as pd,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
def get(d):
    for k in range(4):
        try:
            with fs.open(f'{p}/sst_{d:%Y%m%d}.nc','rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(56.09-1e-4,57.29+1e-4),longitude=slice(10.55-1e-4,11.75+1e-4)).load()
            return x
        except FileNotFoundError: return None
        except Exception as e: err=e
    return ('err',str(err))
t=time.time()
r=get(pd.Timestamp('2009-06-01'));print(time.time()-t,r.analysed_sst.shape,r.latitude.values,r.longitude.values, r.analysed_sst.attrs, r.analysed_sst.dtype)