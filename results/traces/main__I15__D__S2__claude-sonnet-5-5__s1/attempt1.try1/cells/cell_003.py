
import fsspec,xarray as xr,numpy as np
d=xr.open_dataset('/work/s.nc',engine='h5netcdf')
s=d.analysed_sst.sel(latitude=slice(56.13-1e-4,57.33+1e-4),longitude=slice(17.71-1e-4,18.91+1e-4))
print(s.shape,s.latitude.values[[0,-1]],s.longitude.values[[0,-1]])
b=s.sel(time=slice('1991-12-27','2003-01-05')).load()
g=s.sel(time=slice('2019-06-01','2019-08-31')).load()
print(b.shape,g.shape,b.time.values[[0,-1]],np.unique(np.diff(b.time.values)))
b.to_netcdf('/work/b.nc');g.to_netcdf('/work/g.nc')
