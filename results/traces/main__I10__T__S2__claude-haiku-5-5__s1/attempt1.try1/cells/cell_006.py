
import datetime as dt, json, os
import pandas as pd
sub = v.isel(latitude=slice(109,169), longitude=slice(373,433)).sel(time=slice('1991-12-27','2005-08-31')).values.astype(np.float64)
times = pd.to_datetime(ds.time.sel(time=slice('1991-12-27','2005-08-31')).values)
latv = ds.latitude.values[109:169]; lonv = ds.longitude.values[373:433]
print(sub.shape, times[0], times[-1], latv[[0,-1]], lonv[[0,-1]])
# doy mapping (leap calendar)
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
dates = times.normalize()
doys = np.array([doy(d) for d in dates])
# baseline dates
bstart, bend = pd.Timestamp('1992-01-01'), pd.Timestamp('2002-12-31')
base_mask = (dates>=bstart)&(dates<=bend)
print(base_mask.sum(), dates[base_mask][0], dates[base_mask][-1])
# pool per doy
ncell = sub.shape[1]*sub.shape[2]
flat = sub.reshape(len(dates), -1)
thr = np.full((367, ncell), np.nan); clim = np.full((367, ncell), np.nan)
import warnings; warnings.filterwarnings('ignore')
bidx = np.where(base_mask)[0]
for d in range(1,367):
    if d==60: continue
    Bs = bidx[doys[bidx]==d]
    if len(Bs)==0: continue
    pool_idx = set()
    for b in Bs:
        # all date indices with |date - B| <= 5 days
        lo_i, hi_i = b-5, b+5  # times are daily contiguous? check
        pool_idx.update(range(lo_i, hi_i+1))
    pool_idx = sorted(i for i in pool_idx if 0<=i<len(dates))
    P = flat[pool_idx]
    thr[d] = np.nanquantile(P, 0.9, axis=0, method='hazen')
    clim[d] = np.nanmean(P, axis=0)
print(len(dates), (dates.to_series().diff().dropna()==pd.Timedelta('1D')).all())
