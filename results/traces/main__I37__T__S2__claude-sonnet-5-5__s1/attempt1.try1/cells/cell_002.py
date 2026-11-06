
import numpy as np,pandas as pd
sub=ds.sel(latitude=slice(60.09-1e-4,61.29+1e-4),longitude=slice(20.01-1e-4,21.21+1e-4))
print(sub.sizes, sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]])
t=pd.DatetimeIndex(ds.time.values)
print(t.is_unique, (t[1:]-t[:-1]).max())
s=sub.sel(time=slice('1991-12-27','2003-01-05')).analysed_sst.load()
tg=sub.sel(time=slice('2012-06-01','2012-08-31')).analysed_sst.load()
print(s.sizes,tg.sizes,float(s.min()),float(s.max()), float(np.isnan(s).mean()))
