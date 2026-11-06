import numpy as np,pandas as pd
sub=ds.sel(latitude=slice(54.17-1e-4,55.37+1e-4),longitude=slice(13.25-1e-4,14.45+1e-4))
sub=sub.sel(time=slice("1991-12-27","2003-01-05")).analysed_sst.load()
tg=ds.sel(latitude=sub.latitude,longitude=sub.longitude,time=slice("2014-06-01","2014-08-31")).analysed_sst.load()
print(sub.shape,tg.shape,sub.latitude.values[[0,-1]],sub.longitude.values[[0,-1]],float(sub.max()),int(tg.time.size))
print(pd.DatetimeIndex(sub.time).to_series().diff().value_counts().head(3))