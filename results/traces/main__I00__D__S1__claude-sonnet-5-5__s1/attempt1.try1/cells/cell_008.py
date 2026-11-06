import pandas as pd,numpy as np,xarray as xr,json,os
def load(dates):
    out=[]
    for d in dates:
        x=xr.open_dataset(f"/work/d/sst_{d:%Y%m%d}.nc",engine='h5netcdf')
        x=x.sel(latitude=slice(54.13-1e-4,55.33+1e-4),longitude=slice(14.67-1e-4,15.87+1e-4)).analysed_sst
        assert pd.Timestamp(x.time.values[0])==d
        out.append(x.values[0].astype('float64') if False else x.values[0]);lat=x.latitude.values;lon=x.longitude.values
    return np.array(out),lat,lon
bd=pd.date_range('1991-12-27','2003-01-05')
B,lat,lon=load(bd);T,_,_=load(pd.date_range('2004-06-01','2004-08-31'))
print(B.shape,lat,lon,B.dtype,np.nanmean(B))
np.savez('/work/a.npz',B=B,T=T,lat=lat,lon=lon)