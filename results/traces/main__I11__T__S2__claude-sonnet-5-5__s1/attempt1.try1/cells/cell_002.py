import numpy as np,pandas as pd
print(pd.Series(t).diff().value_counts().head())
sub=ds.sel(latitude=slice(55.67-1e-4,56.87+1e-4),longitude=slice(16.45-1e-4,17.65+1e-4))
print(sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]],sub.shape if hasattr(sub,'shape') else sub.analysed_sst.shape)
i0=np.searchsorted(t,np.datetime64('1991-12-27'));i1=np.searchsorted(t,np.datetime64('2003-01-05'),side='right')
j0=np.searchsorted(t,np.datetime64('2021-06-01'));j1=np.searchsorted(t,np.datetime64('2021-08-31'),side='right')
B=sub.analysed_sst.isel(time=slice(i0,i1)).values.astype('float64')
T=sub.analysed_sst.isel(time=slice(j0,j1)).values.astype('float64')
print(B.shape,T.shape,t[i0],t[i1-1],np.isnan(B).mean(),np.nanmean(B))