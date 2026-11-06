import numpy as np,pandas as pd,json,os
la=d.latitude.values;lo=d.longitude.values
li=np.where((la>=59.93-1e-4)&(la<=61.13+1e-4))[0];oi=np.where((lo>=18.69-1e-4)&(lo<=19.89+1e-4))[0]
print(la[li][[0,-1]],lo[oi][[0,-1]],len(li),len(oi))
s=d.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
tt=pd.DatetimeIndex(d.time.values)
bi=np.where((tt>="1991-12-27")&(tt<="2003-01-05"))[0]
print(len(bi),tt[bi[0]],tt[bi[-1]])
B=s.isel(time=slice(bi[0],bi[-1]+1)).values.astype("float64")
ti=np.where((tt>="2009-06-01")&(tt<="2009-08-31"))[0]
T=s.isel(time=slice(ti[0],ti[-1]+1)).values.astype("float64")
print(B.shape,T.shape,np.isnan(B).mean(),B[~np.isnan(B)].mean())