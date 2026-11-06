
import numpy as np
la=ds.latitude.values;lo=ds.longitude.values
li=np.where((la>=56.13-1e-4)&(la<=57.33+1e-4))[0];oi=np.where((lo>=17.71-1e-4)&(lo<=18.91+1e-4))[0]
print(la[li[[0,-1]]],lo[oi[[0,-1]]],len(li),len(oi))
sub=ds.analysed_sst.isel(latitude=slice(li[0],li[-1]+1),longitude=slice(oi[0],oi[-1]+1))
t=ds.time.values
i0=np.searchsorted(t,np.datetime64('1991-12-27'));i1=np.searchsorted(t,np.datetime64('2003-01-06'))
print(t[i0],t[i1-1])
B=sub.isel(time=slice(i0,i1)).values.astype('float64')
j0=np.searchsorted(t,np.datetime64('2019-06-01'));j1=np.searchsorted(t,np.datetime64('2019-09-01'))
T=sub.isel(time=slice(j0,j1)).values.astype('float64')
print(B.shape,T.shape,np.isnan(B).mean(),np.nanmean(T))
