import fsspec,xarray as xr,numpy as np,pandas as pd,os
d=xr.open_dataset('/work/s.nc',engine='h5netcdf')
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=58.69-1e-4)&(la<=59.89+1e-4))[0];oi=np.where((lo>=18.69-1e-4)&(lo<=19.89+1e-4))[0]
print(la[li][[0,-1]],lo[oi][[0,-1]],len(li),len(oi))
a=d.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
s=a.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=a.sel(time=slice('2010-06-01','2010-08-31')).load()
tt=pd.DatetimeIndex(s.time.values);print(len(tt),(tt[1:]-tt[:-1]).max(),np.nanmean(s.values),tg.shape,tg.attrs)
s.to_netcdf('/work/b.nc');tg.to_netcdf('/work/t.nc')