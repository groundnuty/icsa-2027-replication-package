import numpy as np, datetime as dt, json
z=np.load('/tmp/w/sst.npz'); S=z['S']; dates=[dt.date.fromisoformat(x) for x in z['dates']]; lat=z['lat']; lon=z['lon']
idx={d:i for i,d in enumerate(dates)}
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
ny,nx=S.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
bstart=dt.date(1992,1,1); bend=dt.date(2002,12,31)
base=[]; d=bstart
while d<=bend: base.append(d); d+=dt.timedelta(1)
from collections import defaultdict
bydoy=defaultdict(list)
for t in base:
    if t.month==2 and t.day==29: continue  # not possible in leap-doy; handled below
    bydoy[doy(t)].append(t)
# also baseline Feb 29 dates (leap years 1992,1996,2000) map to doy 60 -> excluded
for dd in range(1,367):
    if dd==60: continue
    ts=bydoy.get(dd,[])
    us=set()
    for t in ts:
        for k in range(-5,6): us.add(t+dt.timedelta(k))
    us=sorted(us)
    ii=[idx[u] for u in us if u in idx]
    pool=S[ii]  # n x ny x nx
    with np.errstate(all='ignore'):
        thr[dd]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(A):
    B=A[1:367]  # days 1..366 index 0..365
    out=np.empty_like(B)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(B[ids],axis=0)
    R=np.full_like(A,np.nan); R[1:367]=out; return R
thr_s=smooth(thr); clim_s=smooth(clim)
print(np.isnan(thr_s[1:]).sum(), thr_s[153,30,30], clim_s[153,30,30])