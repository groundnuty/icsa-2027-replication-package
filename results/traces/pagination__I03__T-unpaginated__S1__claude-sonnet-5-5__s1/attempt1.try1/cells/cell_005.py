import fsspec,xarray as xr,pandas as pd,numpy as np,json,os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
def load(dstr):
    for t in range(4):
        try:
            with fs.open(f'{p}/sst_{dstr}.nc','rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(54.165,55.375),longitude=slice(13.245,14.455)).analysed_sst.load()
            return x.values[0],x.latitude.values,x.longitude.values
        except Exception as e: err=e
    raise err
bd=pd.date_range('1991-12-27','2003-01-05'); td=pd.date_range('2014-06-01','2014-08-31')
alld=list(bd.strftime('%Y%m%d'))+list(td.strftime('%Y%m%d'))
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,alld))
lat,lon=res[0][1],res[0][2]
print(len(res),lat[[0,-1]],lon[[0,-1]],res[0][0].shape,res[0][0].dtype)
A=np.stack([r[0] for r in res]).astype(np.float64)
np.save('/tmp/A.npy',A);np.save('/tmp/ll.npy',np.array([lat,lon],dtype=object),allow_pickle=True)