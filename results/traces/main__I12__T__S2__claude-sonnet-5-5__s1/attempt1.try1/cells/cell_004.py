import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(fs.open(p,'rb'),engine='h5netcdf')
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=56.09-1e-4)&(la<=57.29+1e-4))[0];oi=np.where((lo>=10.55-1e-4)&(lo<=11.75+1e-4))[0]
print(la[li][[0,-1]],lo[oi][[0,-1]],len(li),len(oi))
a=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
sub=a.sel(time=slice('1991-12-27','2003-01-05')).load()
tg=a.sel(time=slice('2009-06-01','2009-08-31')).load()
print(sub.shape,tg.shape,sub.time.values[[0,-1]],float(sub.max()),float(sub.min()))
sub.to_netcdf('/tmp/sub.nc');tg.to_netcdf('/tmp/tg.nc')