import numpy as np, datetime as dt, json, os
import xarray as xr
z=np.load('/tmp/sst_region.npz')
arr=z['arr']; days=[dt.date.fromisoformat(s) for s in z['days']]; latv=z['lat']; lonv=z['lon']
start=days[0]; idx_of={dd:i for i,dd in enumerate(days)}
# doy table: fixed leap-year style
cum=[0,31,59,90,120,151,181,212,243,273,304,334]  # days before month in leap-style: Feb29 counted
def doy(date):
    m,dd=date.month,date.day
    base=[0,31,60,91,121,152,182,213,244,274,305,335][m-1]  # Feb-> 31+29 =60 for leap-style
    # leap-style: Jan=0 offset; Feb29 =60, Mar1=61
    if m==2: return 31+dd            # Feb1=32?? fix below
    return base+dd
# explicit mapping: Jan1=1..Feb28=59, Feb29=60, Mar1=61 ...
mdays=[31,29,31,30,31,30,31,31,30,31,30,31]
def doy(date):
    m,dd=date.month,date.day
    return sum(mdays[:m-1])+dd
assert doy(dt.date(2001,2,28))==59 and doy(dt.date(2000,2,29))==60 and doy(dt.date(2001,3,1))==61 and doy(dt.date(2001,12,31))==366
# baseline pool
bstart=dt.date(1992,1,1); bend=dt.date(2002,12,31)
bdates=[bstart+dt.timedelta(i) for i in range((bend-bstart).days+1)]
pool_dates={d:set() for d in range(1,367)}
for b in bdates:
    k=doy(b)
    for off in range(-5,6):
        pool_dates[k].add(b+dt.timedelta(off))
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for k in range(1,367):
    if k==60: continue
    ids=[idx_of[t] for t in sorted(pool_dates[k])]
    P_=arr[ids]
    thr[k]=np.nanquantile(P_,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P_,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    out=np.empty((366,60,60))
    for d in range(1,367):
        ks=[((d-1+o)%366) for o in range(-15,16)]  # 0-based indices
        out[d-1]=np.mean(a[[k+1 for k in ks]],axis=0)
    return out
T=smooth(thr[1:]) if False else None
# smoothing on 1..366 arrays
def smooth366(a366):
    out=np.empty_like(a366)
    for d in range(366):
        ks=[((d+o)%366) for o in range(-15,16)]
        out[d]=np.mean(a366[ks],axis=0)
    return out
thr366=smooth366(thr[1:]); clim366=smooth366(clim[1:])
# target
tmask=[i for i,dd in enumerate(days) if dt.date(2010,6,1)<=dd<=dt.date(2010,8,31)]
tdates=[days[i] for i in tmask]
tsst=arr[tmask]
sea=np.all(np.isfinite(tsst),axis=0)
print('sea cells',sea.sum(), 'nan thr on sea cells', np.isnan(thr366[:,sea]).sum())
tdoy=np.array([doy(dd) for dd in tdates])
Th=thr366[tdoy-1]  # per day
hot=(tsst>=Th)&sea[None]
hot=hot&np.isfinite(Th)
print('hot days',hot.sum())
nT,ny,nx=hot.shape
mhw=np.zeros((nT,ny,nx),bool)
for iy in range(ny):
    for ix in range(nx):
        if not sea[iy,ix]: continue
        h=hot[:,iy,ix]
        # runs
        runs=[];i=0
        while i<nT:
            if h[i]:
                j=i
                while j+1<nT and h[j+1]: j+=1
                if j-i+1>=5: runs.append([i,j])
                i=j+1
            else: i+=1
        # merge
        merged=[]
        for r in runs:
            if merged:
                g=r[0]-merged[-1][1]-1
                if 1<=g<=2 and not h[merged[-1][1]+1:r[0]].any():
                    merged[-1][1]=r[1]; continue
            merged.append(list(r))
        for a,b in merged: mhw[a:b+1,iy,ix]=True
active=mhw.any(axis=(1,2))
events=[];i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        events.append({'onset':tdates[i].isoformat(),'end':tdates[j].isoformat()})
        i=j+1
    else: i+=1
print(len(events)); print(events)
print('mhw cell-days', mhw.sum(), 'active days', active.sum())