import fsspec,xarray as xr,numpy as np,pandas as pd,json,os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.find(p)
d=pd.to_datetime([f[-11:-3] for f in fl],format='%Y%m%d')
def load(f):
    for t in range(5):
        try:
            with xr.open_dataset(fs.open(f,'rb'),engine='h5netcdf') as x:
                x=x.sel(latitude=slice(59.925,61.135),longitude=slice(18.685,19.895))
                return x.analysed_sst.values[0].astype('float64'), x.latitude.values, x.longitude.values
        except Exception as e: err=e
    raise err
m=[(pd.Timestamp('1991-12-27')<=t<=pd.Timestamp('2003-01-05')) or (pd.Timestamp('2007-06-01')<=t<=pd.Timestamp('2007-08-31')) for t in d]
sel=[f for f,k in zip(fl,m) if k]; dd=d[np.array(m)]
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,sel))
A=np.stack([r[0] for r in res]); lat=res[0][1]; lon=res[0][2]
np.savez('/tmp/data.npz',A=A,lat=lat,lon=lon,dd=dd.values)
print(A.shape,lat,lon,np.nanmin(A),np.nanmax(A))