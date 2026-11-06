import pandas as pd,numpy as np,xarray as xr,io,os
from concurrent.futures import ThreadPoolExecutor
os.makedirs('output',exist_ok=True)
dates=pd.date_range('1991-12-27','2003-08-31')
def get(d):
    f=f'{p}/sst_{d:%Y%m%d}.nc'
    for t in range(4):
        try:
            with fs.open(f,'rb') as fh:
                x=xr.open_dataset(fh,engine='h5netcdf').load()
            return x
        except FileNotFoundError: return None
        except Exception as e: err=e
    return ('err',str(err))
r0=get(pd.Timestamp('2003-06-01'));print(r0.analysed_sst.dtype)
la=r0.latitude.values;lo=r0.longitude.values
li=np.where((la>=60.49-1e-4)&(la<=61.69+1e-4))[0];oi=np.where((lo>=17.25-1e-4)&(lo<=18.45+1e-4))[0]
print(la[li],lo[oi])