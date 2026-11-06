
import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
f=fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','rb')
ds=xr.open_dataset(f,engine='h5netcdf')
sub=ds.analysed_sst.sel(latitude=slice(56.629,57.831),longitude=slice(20.229,21.431))
print(sub.shape,sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]])
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2008-06-01','2008-08-31')).load()
print(b.shape,t.shape,np.isnan(b).mean().item(),float(t.min()),float(t.max()))
print(pd.Series(b.time.values).diff().value_counts().head(3))
b.to_netcdf('/tmp/b.nc');t.to_netcdf('/tmp/t.nc')
