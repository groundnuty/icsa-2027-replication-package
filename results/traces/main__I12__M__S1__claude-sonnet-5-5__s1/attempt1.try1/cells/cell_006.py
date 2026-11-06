import os,numpy as np,pandas as pd,xarray as xr,json
p='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(p+'sst_20090601.nc',engine='h5netcdf')
lat=d.latitude.values;lon=d.longitude.values
ii=np.where((lat>=56.09-1e-4)&(lat<=57.29+1e-4))[0];jj=np.where((lon>=10.55-1e-4)&(lon<=11.75+1e-4))[0]
def load(dates):
    out=[]
    for x in dates:
        with xr.open_dataset(f"{p}sst_{x:%Y%m%d}.nc",engine='h5netcdf') as a:
            out.append(a.analysed_sst.values[0][np.ix_(ii,jj)].astype('float64'))
    return np.array(out)
bd=pd.date_range('1991-12-27','2003-01-05')
td=pd.date_range('2009-06-01','2009-08-31')
B=load(bd);T=load(td)
np.save('/tmp/B.npy',B);np.save('/tmp/T.npy',T)
print(B.shape,np.isnan(B).mean(),np.isnan(T).mean())