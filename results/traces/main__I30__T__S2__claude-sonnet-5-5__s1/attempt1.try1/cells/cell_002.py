import numpy as np,pandas as pd
sub=ds.analysed_sst.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895))
print(sub.shape,sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]])
b=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
t=sub.sel(time=slice("2010-06-01","2010-08-31")).load()
print(b.shape,t.shape,np.isnan(b).sum().item(),b.time.size, t.attrs, float(t.max()))