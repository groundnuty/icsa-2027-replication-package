import fsspec,xarray as xr,numpy as np,pandas as pd,os
d=xr.open_dataset('/work/s.nc',engine='h5netcdf')
r=d.analysed_sst.sel(latitude=slice(54.45-1e-4,55.65+1e-4),longitude=slice(16.05-1e-4,17.25+1e-4))
r=r.sel(time=slice('1991-12-27','2021-08-31')).load()
r.to_netcdf('/work/reg.nc')
print(r.shape,r.latitude.values[[0,-1]],r.longitude.values[[0,-1]])
t=r.time.values;print(t[0],len(pd.date_range(t[0],t[-1])),len(t))
print(float(r.max()),float(r.min()))