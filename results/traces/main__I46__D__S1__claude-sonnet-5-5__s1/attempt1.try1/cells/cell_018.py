import numpy as np,pandas as pd
S=np.load('/work/sst.npy');t=pd.DatetimeIndex(np.load('/work/t.npy'))
m=np.nanmean(S,axis=(1,2));d=np.abs(np.diff(m));i=np.argsort(d)[-8:]
for k in i:print(t[k],t[k+1],m[k],m[k+1])