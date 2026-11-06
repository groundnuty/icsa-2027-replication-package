import numpy as np,pandas as pd,json,os
s=d.analysed_sst.sel(latitude=slice(60.49-1e-4,61.69+1e-4),longitude=slice(17.25-1e-4,18.45+1e-4))
s=s.sel(time=slice('1991-12-27','2003-09-05')).load()
print(s.shape,s.latitude.values[[0,-1]],s.longitude.values[[0,-1]])
t=pd.DatetimeIndex(s.time.values);print(t[0],t[-1],len(t),len(pd.date_range(t[0],t[-1])))
print(float(s.min()),float(s.max()))