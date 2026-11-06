import pandas as pd, numpy as np, xarray as xr, time
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=57.83)&(lat<=59.03))[0]
ilon=np.where((lon>=17.41)&(lon<=18.61))[0]
tp = pd.DatetimeIndex(ds.time.values)
t0=pd.Timestamp('1991-12-27'); t1=pd.Timestamp('2003-01-05')
s0=pd.Timestamp('2008-06-01'); s1=pd.Timestamp('2008-08-31')
idx = np.where(((tp>=t0)&(tp<=t1))|((tp>=s0)&(tp<=s1)))[0]
t_s=time.time()
sub = ds.analysed_sst.isel(time=idx, latitude=ilat, longitude=ilon).load()
print(time.time()-t_s, sub.shape, lat[ilat][[0,-1]], lon[ilon][[0,-1]])
sub.to_netcdf('/work/sub.nc')
np.save('/work/subtime.npy', tp[idx].values)