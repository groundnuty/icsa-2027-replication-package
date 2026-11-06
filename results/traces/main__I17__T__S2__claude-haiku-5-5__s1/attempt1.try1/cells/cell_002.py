
sub=ds.sel(latitude=slice(56.63,57.83), longitude=slice(20.23,21.43))
print(sub.latitude.size, sub.longitude.size, float(sub.latitude[0]), float(sub.latitude[-1]), float(sub.longitude[0]), float(sub.longitude[-1]))
import time
t0=time.time()
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2010-06-01','2010-08-31')).load()
print(b.shape, t.shape, time.time()-t0)
