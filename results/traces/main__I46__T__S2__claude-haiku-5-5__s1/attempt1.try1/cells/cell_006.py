
t=time.time()
xb=v.isel(time=slice(i0,i1),latitude=la,longitude=lo).values.astype(np.float64)
tb=tm[i0:i1]
j0=np.searchsorted(tm,np.datetime64('2013-06-01')); j1=np.searchsorted(tm,np.datetime64('2013-08-31'),side='right')
xt=v.isel(time=slice(j0,j1),latitude=la,longitude=lo).values.astype(np.float64)
tt=tm[j0:j1]
np.savez('/tmp/w/cache.npz',xb=xb,tb=tb.astype('datetime64[D]').astype(np.int64),xt=xt,tt=tt.astype('datetime64[D]').astype(np.int64),lat=lat[la],lon=lon[lo])
print(time.time()-t, xb.shape, xt.shape, tt[0], tt[-1], len(tt))
