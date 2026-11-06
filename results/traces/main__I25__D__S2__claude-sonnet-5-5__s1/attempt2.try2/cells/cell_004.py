import xarray as xr,numpy as np,pandas as pd
d=xr.open_dataset('/work/s.nc',engine='h5netcdf')
r=d.analysed_sst.sel(latitude=slice(57.57-1e-4,58.77+1e-4),longitude=slice(10.25-1e-4,11.45+1e-4))
print(r.shape,r.latitude.values[[0,-1]],r.longitude.values[[0,-1]])
a=r.sel(time=slice('1991-12-27','2003-01-05')).load()
t=pd.DatetimeIndex(a.time.values);print(len(t),t[0],t[-1],len(pd.date_range('1991-12-27','2003-01-05')))
tg=r.sel(time=slice('2016-06-01','2016-08-31')).load();print(tg.shape,float(a.min()),np.isnan(a).mean())