
sub=ds.sel(latitude=slice(58.69,59.89),longitude=slice(18.69,19.89))
print(sub.latitude.values, sub.longitude.values)
t=sub.time.sel(time=slice('1991-12-27','2003-01-05'))
print(len(t), t.values[0], t.values[-1])
import pandas as pd
full=pd.date_range('1991-12-27','2003-01-05'); print(len(full))
tt=sub.time.sel(time=slice('2010-06-01','2010-08-31')); print(len(tt))
print(sub.time.sel(time=slice('1991-12-27','2003-01-05')).to_index().equals(full), len(pd.date_range('2010-06-01','2010-08-31')))
