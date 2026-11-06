import numpy as np
from concurrent.futures import ThreadPoolExecutor
lat=d.latitude.values;lon=d.longitude.values
li=np.where((lat>=54.13-1e-4)&(lat<=55.33+1e-4))[0];lj=np.where((lon>=14.67-1e-4)&(lon<=15.87+1e-4))[0]
print(lat[li][[0,-1]],lon[lj][[0,-1]],len(li),len(lj))
def ld(s):
    x=xr.open_dataset(f'/data/icsa2027_data_20261101T090944Z/s1z/sst_{s}.nc',engine='h5netcdf')
    v=x.analysed_sst.isel(time=0,latitude=slice(li[0],li[-1]+1),longitude=slice(lj[0],lj[-1]+1)).values.astype('float64');x.close();return v
bd=pd.date_range('1991-12-27','2003-01-05');td=pd.date_range('2008-06-01','2008-08-31')
with ThreadPoolExecutor(16) as ex:
    B=np.array(list(ex.map(ld,bd.strftime('%Y%m%d'))));T=np.array(list(ex.map(ld,td.strftime('%Y%m%d'))))
print(B.shape,np.isnan(B).mean(),B[~np.isnan(B)].mean())