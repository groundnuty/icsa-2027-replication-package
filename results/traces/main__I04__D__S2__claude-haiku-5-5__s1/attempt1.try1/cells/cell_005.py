
import pandas as pd
t=pd.DatetimeIndex(ds.time.values)
m=((t>=pd.Timestamp('1991-12-27'))&(t<=pd.Timestamp('2003-01-05')))|((t>=pd.Timestamp('2020-06-01'))&(t<=pd.Timestamp('2020-08-31')))
idx=np.where(m)[0]
sub=ds.analysed_sst.isel(time=idx, latitude=la, longitude=lo).load()
print(sub.shape, sub.dtype)
np.savez('/work/sub.npz', sst=sub.values.astype(np.float64), time=t[idx].values.astype('datetime64[D]').astype(np.int64),
         lat=lat[la].astype(np.float64), lon=lon[lo].astype(np.float64))
print(np.isnan(sub.values).sum(), sub.values.min(), sub.values.max())
