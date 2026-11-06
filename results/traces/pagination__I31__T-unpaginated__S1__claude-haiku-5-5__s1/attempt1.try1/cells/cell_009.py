
import numpy as np, datetime as dt, json, os
import xarray as xr
Z=np.load('work/sst.npz')
sst=Z['sst']; dates=[dt.date.fromisoformat(s) for s in Z['dates']]; lat=Z['lat']; lon=Z['lon']
idx={d:i for i,d in enumerate(dates)}
# doy by month/day with Feb=29 always
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    if d.month==2 and d.day==29: return 60
    base=cum[d.month-1]+d.day
    if d.month>2: base+=1  # Feb has 29 days in this mapping
    return base
# check mapping examples
print(doy(dt.date(2001,2,28)),doy(dt.date(2001,3,1)),doy(dt.date(2001,12,31)),doy(dt.date(2001,1,1)),doy(dt.date(2000,2,29)),doy(dt.date(2001,6,1)))
bl_start=dt.date(1992,1,1); bl_end=dt.date(2002,12,31)
baseline_dates=[bl_start+dt.timedelta(days=i) for i in range((bl_end-bl_start).days+1)]
# window pools
pool_idx={d:[] for d in range(1,367)}
for b in baseline_dates:
    dd=doy(b)
    if dd==60: continue
    pool_idx[dd]+=[idx[b+dt.timedelta(days=k)] for k in range(-5,6)]
for d in pool_idx: pool_idx[d]=sorted(set(pool_idx[d]))
print(len(pool_idx[1]),len(pool_idx[59]),len(pool_idx[366]), len(pool_idx[60]))
