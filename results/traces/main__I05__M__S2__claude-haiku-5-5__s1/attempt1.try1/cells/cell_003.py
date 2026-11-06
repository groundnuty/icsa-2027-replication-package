
import xarray as xr, numpy as np, pandas as pd, time
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
t0=time.time()
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lo=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]])
sub=ds.analysed_sst.isel(latitude=la,longitude=lo)
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2021-06-01','2021-08-31')).load()
print(b.shape,t.shape,time.time()-t0)
