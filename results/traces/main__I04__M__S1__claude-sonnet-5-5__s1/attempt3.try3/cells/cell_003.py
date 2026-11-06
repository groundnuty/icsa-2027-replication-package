import numpy as np
from concurrent.futures import ThreadPoolExecutor
lat=d.latitude.values;lon=d.longitude.values
li=np.where((lat>=54.39-1e-4)&(lat<=55.59+1e-4))[0];lj=np.where((lon>=18.25-1e-4)&(lon<=19.45+1e-4))[0]
print(lat[li][[0,-1]],lon[lj][[0,-1]])
def rd(x):
    a=xr.open_dataset(p+f"sst_{x:%Y%m%d}.nc",engine='h5netcdf')
    v=a.analysed_sst.isel(time=0,latitude=slice(li[0],li[-1]+1),longitude=slice(lj[0],lj[-1]+1)).values.astype('float64');a.close();return v
def load(a,b):
    ds=[a+dt.timedelta(i) for i in range((b-a).days+1)]
    with ThreadPoolExecutor(16) as ex: return ds,np.array(list(ex.map(rd,ds)))
bd,B=load(dt.date(1991,12,27),dt.date(2003,1,5))
td,T=load(dt.date(2020,6,1),dt.date(2020,8,31))
print(B.shape,T.shape,np.nanmean(T),np.isnan(B).mean())