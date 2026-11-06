
import time
t=time.time()
sub = v.isel(latitude=slice(109,169), longitude=slice(373,433), time=slice(0,50)).values
print(sub.shape, time.time()-t, np.isnan(sub).mean())
print(ds.time.values[:3], ds.time.values[-1])
