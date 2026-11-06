
import fsspec,xarray as xr,numpy as np,pandas as pd
ds=xr.open_dataset('/work/s.nc',engine='h5netcdf')
la=ds.latitude.values.astype('f8');lo=ds.longitude.values.astype('f8')
li=np.where((la>=54.39-1e-4)&(la<=55.59+1e-4))[0];oi=np.where((lo>=18.25-1e-4)&(lo<=19.45+1e-4))[0]
print(la[li],lo[oi])
t=pd.DatetimeIndex(ds.time.values);print(len(t),t.is_unique,(np.diff(t)!=np.timedelta64(1,'D')).sum())
sub=ds.analysed_sst.isel(latitude=li,longitude=oi)
m=(t>='1991-12-27')&(t<='2003-01-05')|(t>='2020-06-01')&(t<='2020-08-31')
X=sub.isel(time=np.where(m)[0]).load();print(X.shape)
X.to_netcdf('/work/x.nc')
