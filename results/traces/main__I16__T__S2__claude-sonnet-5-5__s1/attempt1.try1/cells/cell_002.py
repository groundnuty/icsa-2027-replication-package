
import numpy as np,pandas as pd
sub=ds.analysed_sst.sel(latitude=slice(56.629,57.831),longitude=slice(20.229,21.431))
print(sub.shape,sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]])
b=sub.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.sel(time=slice('2008-06-01','2008-08-31')).load()
print(b.shape,t.shape,np.isnan(b).mean().item(),float(t.min()),float(t.max()))
