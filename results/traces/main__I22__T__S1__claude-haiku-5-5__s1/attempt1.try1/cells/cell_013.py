
import numpy as np, datetime as dt, json, os
g=np.load('/tmp/sub/grid.npz'); 
lat=g['lat']; lon=g['lon']
il=np.where((lat>=57.41)&(lat<=58.61))[0]; jl=np.where((lon>=18.69)&(lon<=19.89))[0]
LAT=lat[il]; LON=lon[jl]
print(len(LAT),len(LON),LAT[[0,-1]],LON[[0,-1]])
start=dt.date(1991,12,27); end=dt.date(2004,8,31)
ndays=(end-start).days+1
cube=np.full((ndays,len(LAT),len(LON)),np.nan)
for i in range(ndays):
    d=start+dt.timedelta(i)
    cube[i]=np.load(f"/tmp/sub/{d:%Y%m%d}.npy").astype(np.float64)
dates=[start+dt.timedelta(i) for i in range(ndays)]
idx={d:i for i,d in enumerate(dates)}
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday  # leap-year calendar mapping
# target
tgt=[d for d in dates if dt.date(2004,6,1)<=d<=dt.date(2004,8,31)]
tgt_idx=[idx[d] for d in tgt]
T=cube[tgt_idx]
sea=np.all(np.isfinite(T),axis=0)
print('target days',len(tgt),'sea cells',sea.sum(), 'target-day NaN count',np.isnan(T).sum())
# baseline pools
bstart=dt.date(1992,1,1); bend=dt.date(2002,12,31)
pool_dates={d:set() for d in range(1,367)}
for Y in range(1992,2003):
    for d in range(1,367):
        pass
# build by iterating baseline dates
bdates=[dt.date(1992,1,1)+dt.timedelta(i) for i in range((bend-bstart).days+1)]
for b in bdates:
    k=doy(b)
    if k==60: continue
    for s in range(-5,6):
        t=b+dt.timedelta(s)
        pool_dates[k].add(t)
print('pool sizes', {k:len(pool_dates[k]) for k in [1,59,61,150,366]})
