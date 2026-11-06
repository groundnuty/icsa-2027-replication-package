import os,json,numpy as np,pandas as pd,xarray as xr
D='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(D+'sst_20170601.nc',engine='h5netcdf')
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=62.25-1e-4)&(la<=63.45+1e-4))[0];oi=np.where((lo>=18.73-1e-4)&(lo<=19.93+1e-4))[0]
def load(dates):
    out=[]
    for t in dates:
        x=xr.open_dataset(D+f"sst_{t:%Y%m%d}.nc",engine='h5netcdf')
        out.append(x.analysed_sst.values[0][li[0]:li[-1]+1,oi[0]:oi[-1]+1].astype('float64'));x.close()
    return np.array(out)
bd=pd.date_range('1991-12-27','2003-01-05');B=load(bd)
td=pd.date_range('2017-06-01','2017-08-31');T=load(td)
np.save('/tmp/B.npy',B);np.save('/tmp/T.npy',T)
print(B.shape,np.isnan(B).mean(),np.nanmin(T),np.nanmax(T),np.isnan(T).all(0).sum())