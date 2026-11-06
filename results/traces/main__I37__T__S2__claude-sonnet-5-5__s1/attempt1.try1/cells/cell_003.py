
import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.sel(latitude=slice(60.09-1e-4,61.29+1e-4),longitude=slice(20.01-1e-4,21.21+1e-4))
print(sub.sizes, sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]])
t=pd.DatetimeIndex(ds.time.values)
print(t.is_unique, (t[1:]-t[:-1]).max())
s=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
tg=sub.sel(time=slice('2012-06-01','2012-08-31')).analysed_sst.load()
print(s.sizes,tg.sizes,float(s.min()),float(s.max()), float(np.isnan(s).mean()))
s.to_netcdf('/tmp/s.nc');tg.to_netcdf('/tmp/tg.nc')
