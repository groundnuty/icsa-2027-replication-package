
import numpy as np,pandas as pd
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=57.13-1e-4)&(la<=58.33+1e-4))[0];oi=np.where((lo>=22.79-1e-4)&(lo<=23.99+1e-4))[0]
print(la[li][[0,-1]],lo[oi][[0,-1]],len(li),len(oi))
t=pd.DatetimeIndex(ds.time.values)
s=t.searchsorted(pd.Timestamp('1991-12-27'));e=t.searchsorted(pd.Timestamp('2003-01-05'),side='right')
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
B=sub.isel(time=slice(s,e)).values.astype('f8');print(B.shape,np.isnan(B).mean(), np.nanmean(B))
ts=t.searchsorted(pd.Timestamp('2010-06-01'));te=t.searchsorted(pd.Timestamp('2010-08-31'),side='right')
T=sub.isel(time=slice(ts,te)).values.astype('f8');print(T.shape)
