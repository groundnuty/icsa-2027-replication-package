
import pandas as pd
sub = v.isel(latitude=la, longitude=lo)
base = sub.sel(time=slice('1991-12-27','2003-01-05')).load()
tgt = sub.sel(time=slice('2013-06-01','2013-08-31')).load()
print(base.shape, tgt.shape, base.time.values[[0,-1]], tgt.time.values[[0,-1]])
print(np.isnan(base.values).mean(), np.isnan(tgt.values).mean())
