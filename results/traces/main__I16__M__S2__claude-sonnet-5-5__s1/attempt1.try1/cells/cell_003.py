import xarray as xr,numpy as np,pandas as pd
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
d=xr.open_dataset(p,engine="h5netcdf")
la=d.latitude.values;lo=d.longitude.values
i=np.where((la>=56.63-1e-4)&(la<=57.83+1e-4))[0];j=np.where((lo>=20.23-1e-4)&(lo<=21.43+1e-4))[0]
print(la[i][[0,-1]],lo[j][[0,-1]],len(i),len(j))
sub=d.analysed_sst.isel(latitude=slice(i[0],i[-1]+1),longitude=slice(j[0],j[-1]+1))
t=d.time.values
b0=np.searchsorted(t,np.datetime64("1991-12-27"));b1=np.searchsorted(t,np.datetime64("2003-01-05"),side="right")
print(t[b0],t[b1-1],len(t[b0:b1]))
base=sub.isel(time=slice(b0,b1)).values.astype("float64")
tg=sub.sel(time=slice("2008-06-01","2008-08-31")).load()
print(tg.shape, np.nanmean(base), np.nanmean(tg.values))