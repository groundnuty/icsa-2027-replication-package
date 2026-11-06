import os,xarray as xr,pandas as pd,numpy as np
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_20090601.nc',engine='h5netcdf')
lat=ds.latitude.values;lon=ds.longitude.values
li=np.where((lat>=61.57-1e-4)&(lat<=62.77+1e-4))[0];lj=np.where((lon>=20.17-1e-4)&(lon<=21.37+1e-4))[0]
print(lat[li][[0,-1]],lon[lj][[0,-1]],len(li),len(lj))
def rd(s):
    with xr.open_dataset(f'{d}/sst_{s}.nc',engine='h5netcdf') as x:
        return x.analysed_sst.isel(time=0,latitude=slice(li[0],li[-1]+1),longitude=slice(lj[0],lj[-1]+1)).values.astype('float64')
dates=pd.date_range('1991-12-27','2003-01-05')
with ThreadPoolExecutor(16) as ex: B=np.array(list(ex.map(rd,dates.strftime('%Y%m%d'))))
td=pd.date_range('2009-06-01','2009-08-31')
with ThreadPoolExecutor(16) as ex: T=np.array(list(ex.map(rd,td.strftime('%Y%m%d'))))
print(B.shape,T.shape,np.nanmean(T),np.isnan(B).mean(),np.nanmin(T))
np.save('/tmp/B.npy',B);np.save('/tmp/T.npy',T)