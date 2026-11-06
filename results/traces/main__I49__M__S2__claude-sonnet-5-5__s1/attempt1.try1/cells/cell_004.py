import xarray as xr,numpy as np,pandas as pd
p="/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds=xr.open_dataset(p,engine="h5netcdf");t=ds.time.values
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=64.51-1e-4)&(la<=65.71+1e-4))[0];oi=np.where((lo>=21.97-1e-4)&(lo<=23.17+1e-4))[0]
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
print(la[li[[0,-1]]],lo[oi[[0,-1]]])
tt=pd.DatetimeIndex(t)
b0=np.searchsorted(tt,pd.Timestamp("1991-12-27"));b1=np.searchsorted(tt,pd.Timestamp("2003-01-05"),side="right")
print(tt[b0],tt[b1-1],b1-b0)
base=sub.isel(time=slice(b0,b1)).values.astype("float64");bt=tt[b0:b1]
tg=sub.sel(time=slice("2019-06-01","2019-08-31")).load();print(tg.shape,float(tg.max()),np.isnan(base).mean(),np.nanmax(base))
print(len(pd.date_range("1991-12-27","2003-01-05")))