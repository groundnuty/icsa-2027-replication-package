
import time
t=time.time()
x=v.isel(time=0,latitude=la,longitude=lo).values
print(time.time()-t, x.shape, np.isnan(x).mean(), np.nanmin(x), np.nanmax(x))
tm=ds.time.values
i0=np.searchsorted(tm,np.datetime64('1991-12-27')); i1=np.searchsorted(tm,np.datetime64('2003-01-05'),side='right')
print(i0,i1,tm[i0],tm[i1-1])
