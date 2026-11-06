import pandas as pd, numpy as np, xarray as xr, time
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
t = ds.time.values
t0=pd.Timestamp('1991-12-27'); t1=pd.Timestamp('2003-01-05')
s0=pd.Timestamp('2008-06-01'); s1=pd.Timestamp('2008-08-31')
tp = pd.DatetimeIndex(t)
mask_t = ((tp>=t0)&(tp<=t1))|((tp>=s0)&(tp<=s1))
idx = np.where(mask_t)[0]
print(len(idx), tp[idx[0]], tp[idx[-1]], np.all(np.diff(idx)>0))
# check contiguous coverage
need = pd.date_range(t0,t1).append(pd.date_range(s0,s1))
print(len(need), set(need)-set(tp[idx]) == set())
t_s=time.time()
sub = ds.analysed_sst.isel(time=idx, latitude=ilat, longitude=ilon).load()
print(time.time()-t_s, sub.shape)
sub.to_netcdf('/work/sub.nc')
np.save('/work/subtime.npy', tp[idx].values)