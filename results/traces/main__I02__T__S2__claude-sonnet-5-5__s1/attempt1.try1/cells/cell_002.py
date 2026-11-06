
import numpy as np,pandas as pd
sub=ds.analysed_sst.sel(latitude=slice(54.17-1e-4,55.37+1e-4),longitude=slice(13.25-1e-4,14.45+1e-4))
sub=sub.sel(time=slice("1991-12-27","2003-01-05")).load() if False else sub
b=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
t=sub.sel(time=slice("2004-06-01","2004-08-31")).load()
print(b.shape,t.shape,b.latitude.values[[0,-1]],b.longitude.values[[0,-1]],ds.analysed_sst.attrs)
print(np.isnan(b.values).mean(), np.nanmean(t.values))
