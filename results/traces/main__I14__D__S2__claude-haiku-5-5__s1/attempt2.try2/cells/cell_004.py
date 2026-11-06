
import time
t0=time.time()
li=np.where(m_la)[0]; oi=np.where(m_lo)[0]
sub = ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1), longitude=slice(oi[0],oi[-1]+1))
tb = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tt = sub.sel(time=slice('2015-06-01','2015-08-31')).load()
print(time.time()-t0, tb.shape, tt.shape)
A=tb.values.astype(np.float64); T=tt.values.astype(np.float64)
print(np.isfinite(A).mean(), np.isfinite(T).mean())
sea = np.all(np.isfinite(T),axis=0)
print(sea.sum(), sea.size, np.isfinite(A).all(axis=0).sum())
print(tt.latitude.values[:3], tt.longitude.values[:3], tt.time.values[[0,-1]], T.min(), T.max())
