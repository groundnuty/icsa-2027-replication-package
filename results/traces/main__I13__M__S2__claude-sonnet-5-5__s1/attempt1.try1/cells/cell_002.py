import numpy as np, pandas as pd
s=d.sel(latitude=slice(56.09-1e-4,57.29+1e-4),longitude=slice(10.55-1e-4,11.75+1e-4)).analysed_sst
print(s.shape, s.latitude.values[[0,-1]], s.longitude.values[[0,-1]])
b=s.sel(time=slice("1991-12-27","2003-01-05")).load()
t=s.sel(time=slice("2021-06-01","2021-08-31")).load()
print(b.shape,t.shape, pd.Series(b.time.values).diff().value_counts().head(), np.nanmean(t.values))