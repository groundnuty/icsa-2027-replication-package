
import numpy as np, pandas as pd, json
z=np.load('/work/sub.npz')
sst=z['sst']; dates=pd.to_datetime(z['time'].astype('datetime64[D]')); lat=z['lat']; lon=z['lon']
Ttot=sst.shape[0]
# day-of-year by month/day: non-leap calendar, Feb29=60
def doy(ts):
    ref=pd.Timestamp('2001-01-01')
    d=ts.map(lambda x: pd.Timestamp(2001,x.month,x.day) if not (x.month==2 and x.day==29) else None)
    out=np.array([ (x.dayofyear if not (x.month==2 and x.day==29) else 60) for x in ts])
    # non-leap doy: for dates after Feb29 in leap years subtract 1
    res=[]
    for x in ts:
        if x.month==2 and x.day==29: res.append(60)
        else:
            base=pd.Timestamp(2001,x.month,x.day).dayofyear
            res.append(base)
    return np.array(res)
D=doy(dates)
dmap={dt:i for i,dt in enumerate(dates)}
base_B=pd.date_range('1992-01-01','2002-12-31')
pools={}
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
from numpy import nan
for d in range(1,367):
    if d==60: continue
    Bs=[b for b in base_B if doy(pd.DatetimeIndex([b]))[0]==d]
    vals=[]
    for b in Bs:
        for k in range(-5,6):
            dd=b+pd.Timedelta(days=k)
            vals.append(sst[dmap[dd]])
    P=np.stack(vals)  # (n,60,60)
    P=P.reshape(P.shape[0],-1)
    with np.errstate(all='ignore'):
        thr[d]=np.nanpercentile(P,90,axis=0,method='hazen').reshape(60,60)
        clim[d]=np.nanmean(P,axis=0).reshape(60,60)
    pools[d]=P.shape[0]
print(set(pools.values()), min(pools), max(pools))
