import fsspec,xarray as xr,numpy as np,pandas as pd,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
d=pd.date_range('1991-12-27','2003-01-05'); t=pd.date_range('2014-06-01','2014-08-31')
alld=list(d)+list(t)
def load(x):
    for k in range(4):
        try:
            with xr.open_dataset(fs.open(f'{p}/sst_{x:%Y%m%d}.nc','rb'),engine='h5netcdf') as a:
                a=a.sel(latitude=slice(57.12,58.34),longitude=slice(22.78,24.0))
                return a.analysed_sst.values[0].astype('float64'),a.latitude.values,a.longitude.values
        except Exception as e: err=e
    raise err
t0=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,alld))
print(time.time()-t0)
lat,lon=res[0][1],res[0][2];print(lat,lon,res[0][0].shape)
np.save('/tmp/a.npy',np.stack([r[0] for r in res]));np.save('/tmp/lat.npy',lat);np.save('/tmp/lon.npy',lon)