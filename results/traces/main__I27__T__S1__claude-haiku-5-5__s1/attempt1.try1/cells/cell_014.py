import numpy as np, datetime as dt, json, os
import xarray as xr
c=np.load('/tmp/cache.npz')
V=c['V']; LA=c['LA']; LO=c['LO']; dates=[dt.datetime.strptime(s,'%Y%m%d').date() for s in c['dates']]
start=dates[0]
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
base_lo,base_hi=dt.date(1992,1,1),dt.date(2002,12,31)
ndate=len(dates)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
bidx_by_doy={}
for b in [d for d in dates if base_lo<=d<=base_hi]:
    bidx_by_doy.setdefault(doy(b),[]).append(b)
for d in range(1,367):
    if d==60: continue
    idxs=set()
    for b in bidx_by_doy[d]:
        for k in range(-5,6):
            idxs.add((b+dt.timedelta(k)-start).days)
    idxs=sorted(i for i in idxs if 0<=i<ndate)
    pool=V[idxs]
    with np.errstate(all='ignore'):
        thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]; out=np.empty_like(a)
    for i in range(366):
        out[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thr_s=smooth(thr)

tidx=[i for i,d in enumerate(dates) if dt.date(2008,6,1)<=d<=dt.date(2008,8,31)]
tdates=[dates[i] for i in tidx]
T=V[tidx]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'target days',len(tdates),tdates[0],tdates[-1])
doys=np.array([doy(d) for d in tdates])
th=thr_s[doys-1]
with np.errstate(invalid='ignore'):
    hot=(T>=th)&sea[None]
def runs(b):
    out=[];n=len(b);i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
mhw=np.zeros(hot.shape,bool); nseg=0
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        segs=[s for s in runs(hot[:,y,x]) if s[1]-s[0]+1>=5]
        if not segs: continue
        merged=[list(segs[0])]
        for s in segs[1:]:
            if s[0]-merged[-1][1]-1<=2: merged[-1][1]=s[1]
            else: merged.append(list(s))
        for a,bb in merged:
            mhw[a:bb+1,y,x]=True; nseg+=1
print('cell MHW segments',nseg)
active=mhw.any(axis=(1,2))
events=[]; i=0; n=len(active)
while i<n:
    if active[i]:
        j=i
        while j+1<n and active[j+1]: j+=1
        events.append({"onset":tdates[i].isoformat(),"end":tdates[j].isoformat()}); i=j+1
    else: i+=1
print(events)
print('hot any',hot.any(axis=(1,2)).sum(),'active days',active.sum())
print('mhw cell-days',mhw.sum(), 'sea cell-days', sea.sum()*92)