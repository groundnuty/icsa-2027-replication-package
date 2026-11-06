
import numpy as np, datetime as dt
Z=np.load('work/sst.npz')
sst=Z['sst']; dates=[dt.date.fromisoformat(s) for s in Z['dates']]; lat=Z['lat']; lon=Z['lon']
idx={d:i for i,d in enumerate(dates)}
cum=[0,31,60,91,121,152,182,213,244,274,305,335]
def doy(d):
    if d.month==2 and d.day==29: return 60
    return cum[d.month-1]+d.day
print(doy(dt.date(2001,2,28)),doy(dt.date(2001,3,1)),doy(dt.date(2001,12,31)),doy(dt.date(2001,1,1)),doy(dt.date(2000,2,29)),doy(dt.date(2001,6,1)), doy(dt.date(2001,8,31)))
bl=[dt.date(1992,1,1)+dt.timedelta(days=i) for i in range((dt.date(2002,12,31)-dt.date(1992,1,1)).days+1)]
pool_idx={d:set() for d in range(1,367)}
for b in bl:
    dd=doy(b)
    if dd==60: continue
    pool_idx[dd].update(idx[b+dt.timedelta(days=k)] for k in range(-5,6))
pool_idx={d:sorted(v) for d,v in pool_idx.items()}
print(len(pool_idx[1]),len(pool_idx[59]),len(pool_idx[366]), len(pool_idx[60]))
# check dates in pools for doy 1 and 366
print([str(dates[i]) for i in pool_idx[366][:3]], [str(dates[i]) for i in pool_idx[1][:2]])
