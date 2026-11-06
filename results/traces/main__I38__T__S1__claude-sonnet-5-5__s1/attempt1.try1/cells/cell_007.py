import fsspec,pandas as pd,numpy as np,xarray as xr,os
from concurrent.futures import ThreadPoolExecutor
def get(d):
    fs=fsspec.filesystem('onedata')
    f=f'icsa2027_data_20261101T090944Z/s1z/sst_{d:%Y%m%d}.nc'
    err=None
    for t in range(4):
        try:
            with fs.open(f,'rb') as fh:
                return xr.open_dataset(fh,engine='h5netcdf').load()
        except FileNotFoundError: return None
        except Exception as e: err=e
    return ('err',str(err))
r0=get(pd.Timestamp('2003-06-01'));print(r0.analysed_sst.dtype)
la=r0.latitude.values;lo=r0.longitude.values
li=np.where((la>=60.49-1e-4)&(la<=61.69+1e-4))[0];oi=np.where((lo>=17.25-1e-4)&(lo<=18.45+1e-4))[0]
print(la[li],lo[oi])