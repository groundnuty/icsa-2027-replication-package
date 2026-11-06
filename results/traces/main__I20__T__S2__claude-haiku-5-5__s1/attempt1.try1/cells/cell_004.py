
import time
t=time.time()
x=v.isel(time=slice(0,1),latitude=li,longitude=lo).values
print(time.time()-t, x.shape, np.nanmin(x), np.nanmax(x), np.isnan(x).mean())
