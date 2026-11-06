
import xarray as xr,numpy as np,pandas as pd
s=xr.open_dataset('/work/sub.nc').analysed_sst
v=s.values.astype('float64'); t=pd.DatetimeIndex(s.time.values)
cum=np.array([0,31,60,91,121,152,182,213,244,274,305,335]);doy=cum[t.month-1]+t.day
ti=np.where((t>='2004-06-01')&(t<='2004-08-31'))[0]
x=v[ti];sea=np.isfinite(x).all(0)
b=np.where((t>='1992-01-01')&(t<='2002-12-31')&np.isin(t.month,[6,7,8]))[0]
print(np.nanmean(v[b][:,sea]),np.nanmean(x[:,sea]),sea.sum(), np.isfinite(v[ti]).all((1,2)).sum())
