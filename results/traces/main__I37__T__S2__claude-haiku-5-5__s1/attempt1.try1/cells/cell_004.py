
import pandas as pd
b=sub.analysed_sst.sel(time=slice('1991-12-27','2003-01-05')).load()
t=sub.analysed_sst.sel(time=slice('2012-06-01','2012-08-31')).load()
print(b.shape,t.shape)
print(np.isnan(b.values).sum(), np.isnan(t.values).sum())
