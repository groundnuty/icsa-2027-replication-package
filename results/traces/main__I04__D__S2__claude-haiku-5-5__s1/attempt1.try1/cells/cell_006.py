
import xarray, numpy as np, pandas as pd
ds = xarray.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]; lo=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
t=pd.DatetimeIndex(ds.time.values)
m=((t>=pd.Timestamp('1991-12-27'))&(t<=pd.Timestamp('2003-01-05')))|((t>=pd.Timestamp('2020-06-01'))&(t<=pd.Timestamp('2020-08-31')))
idx=np.where(m)[0]
sub=ds.analysed_sst.isel(time=idx, latitude=la, longitude=lo).load()
print(sub.shape, sub.dtype)
np.savez('/work/sub.npz', sst=sub.values.astype(np.float64), time=t[idx].values.astype('datetime64[D]').astype(np.int64),
         lat=lat[la].astype(np.float64), lon=lon[lo].astype(np.float64))
print(np.isnan(sub.values).sum(), np.nanmin(sub.values), np.nanmax(sub.values))
