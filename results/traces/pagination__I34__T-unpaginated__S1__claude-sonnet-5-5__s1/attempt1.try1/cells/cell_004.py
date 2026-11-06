import numpy as np
from concurrent.futures import ThreadPoolExecutor
def load(f):
    for t in range(4):
        try:
            with xr.open_dataset(fs.open(f,'rb'),engine='h5netcdf') as x:
                x=x.sel(latitude=slice(59.925,61.135),longitude=slice(18.685,19.895))
                return x.analysed_sst.values[0].astype('float64'), x.latitude.values, x.longitude.values
        except Exception as e: err=e
    raise err
sel=[f for f,t in zip(fl,d) if (pd.Timestamp('1991-12-27')<=t<=pd.Timestamp('2003-01-05')) or (pd.Timestamp('2007-06-01')<=t<=pd.Timestamp('2007-08-31'))]
dd=[t for f,t in zip(fl,d) if f in set(sel)]
print(len(sel))
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,sel))
print(res[0][0].shape,res[0][1],res[0][2]);print(np.nanmin(res[0][0]),np.nanmax(res[0][0]))