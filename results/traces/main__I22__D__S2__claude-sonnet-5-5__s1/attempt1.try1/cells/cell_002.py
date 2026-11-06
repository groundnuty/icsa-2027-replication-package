
import numpy as np,pandas as pd
s=d.analysed_sst.sel(latitude=slice(57.405,58.615),longitude=slice(18.685,19.895))
s=s.sel(time=slice('1991-12-27','2004-08-31')).load()
print(s.shape,s.latitude.values[[0,-1]],s.longitude.values[[0,-1]])
t=pd.DatetimeIndex(s.time.values);print(len(t),t.min(),t.max(),pd.Series(t).diff().value_counts().head())
print(s.dtype, float(s.isnull().mean()))
