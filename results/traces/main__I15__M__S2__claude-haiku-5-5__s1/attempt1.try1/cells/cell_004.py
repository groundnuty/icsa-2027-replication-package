
import pandas as pd
sub=ds.analysed_sst.isel(latitude=ila,longitude=ilo)
base=sub.sel(time=slice('1991-12-27','2003-01-05')).values.astype(np.float64)
btime=pd.DatetimeIndex(sub.sel(time=slice('1991-12-27','2003-01-05')).time.values)
tgt=sub.sel(time=slice('2019-06-01','2019-08-31'))
ttime=pd.DatetimeIndex(tgt.time.values); tv=tgt.values.astype(np.float64)
print(base.shape, tv.shape, np.isnan(base).mean(), np.isnan(tv).mean())
print(np.nanmin(tv), np.nanmax(tv))
