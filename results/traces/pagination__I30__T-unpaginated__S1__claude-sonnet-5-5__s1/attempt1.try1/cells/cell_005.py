import fsspec,xarray as xr, numpy as np, pandas as pd, json, os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
base=pd.date_range('1991-12-27','2003-01-05'); tgt=pd.date_range('2010-06-01','2010-08-31')
need=base.append(tgt)
def load(d):
    for _ in range(5):
        try:
            with xr.open_dataset(fs.open(f"{p}/sst_{d:%Y%m%d}.nc",'rb'),engine='h5netcdf') as x:
                x=x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895))
                return x.analysed_sst.values[0].astype('float64'),x.latitude.values,x.longitude.values
        except Exception as e: err=e
    raise err
with ThreadPoolExecutor(16) as ex: r=list(ex.map(load,need))
lat,lon=r[0][1],r[0][2];print(lat[[0,-1]],lon[[0,-1]],len(lat),len(lon))
A=np.stack([a[0] for a in r]);print(A.shape,np.nanmin(A),np.nanmax(A))
np.save('/tmp/A.npy',A);np.save('/tmp/lat.npy',lat);np.save('/tmp/lon.npy',lon)