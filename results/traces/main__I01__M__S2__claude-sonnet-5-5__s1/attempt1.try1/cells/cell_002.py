import numpy as np,pandas as pd,json,os
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=54.13-1e-4)&(la<=55.33+1e-4))[0];oi=np.where((lo>=14.67-1e-4)&(lo<=15.87+1e-4))[0]
print(la[li][[0,-1]],lo[oi][[0,-1]],len(li),len(oi))
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
s=sub.sel(time=slice("1991-12-27","2003-01-05")).load()
tg=sub.sel(time=slice("2008-06-01","2008-08-31")).load()
print(s.shape,tg.shape,float(tg.max()))