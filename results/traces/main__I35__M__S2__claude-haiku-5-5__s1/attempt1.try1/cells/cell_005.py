
import xarray as xr, numpy as np, pandas as pd
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
li=np.where((lat>=59.93-1e-6)&(lat<=61.13+1e-6))[0]; lj=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
sub=ds.analysed_sst.isel(latitude=li,longitude=lj)
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2009-06-01','2009-08-31')).load()
print(b.shape,t.shape, b.time.values[0], b.time.values[-1], t.time.values[0], t.time.values[-1])
print(np.isnan(t.values).sum(), np.nanmin(t.values), np.nanmax(t.values))
print(np.isnan(b.values).sum(), b.size)
