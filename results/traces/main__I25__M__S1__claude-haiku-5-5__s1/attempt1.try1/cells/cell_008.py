code=r'''
import numpy as np, datetime as dt, json, os, xarray as xr, warnings
warnings.filterwarnings('ignore')
z=np.load('/tmp/sub.npz'); A=z['A']; dates=[dt.date.fromisoformat(s) for s in z['dates']]; latv=z['lat']; lonv=z['lon']
def doy(x):
    leap=(x.year%4==0 and x.year%100!=0) or x.year%400==0
    t=x.timetuple().tm_yday
    if leap: return t
    return t+1 if x.month>=3 else t
idx={x:i for i,x in enumerate(dates)}
ny,nx=A.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base=[x for x in dates if dt.date(1992,1,1)<=x<=dt.date(2002,12,31)]
bydoy={}
for b in base: bydoy.setdefault(doy(b),[]).append(b)
for dd in range(1,367):
    if dd==60: continue
    ids=set()
    for b in bydoy.get(dd,[]):
        for k in range(-5,6):
            x=b+dt.timedelta(k)
            if x in idx: ids.add(idx[x])
    ids=sorted(ids)
    P=A[ids]
    thr[dd]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[dd]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
T=thr[1:367]; C=clim[1:367]
def sm(a):
    return np.array([a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0) for i in range(366)])
Ts=sm(T); Cs=sm(C)
tgt=[x for x in dates if dt.date(2016,6,1)<=x<=dt.date(2016,8,31)]
ti=[idx[x] for x in tgt]
S=A[ti]
sea=np.all(np.isfinite(S),axis=0)
print('sea cells', sea.sum(), 'target days', len(tgt), 'bl range', base[0], base[-1], 'ids last', len(ids))
doys=np.array([doy(x) for x in tgt])
Tt=Ts[doys-1]
hot=(S>=Tt)&sea[None]
mhw=np.zeros_like(hot)
ncell=0; gapcases=0
for j in range(ny):
    for i in range(nx):
        if not sea[j,i]: continue
        h=hot[:,j,i]
        runs=[]; t=0; n=len(h)
        while t<n:
            if h[t]:
                s0=t
                while t<n and h[t]: t+=1
                if t-s0>=5: runs.append([s0,t-1])
            else: t+=1
        merged=[]
        for r in runs:
            if merged and r[0]-merged[-1][1]-1 in (1,2):
                merged[-1][1]=r[1]
            else: merged.append(list(r))
        for a,b in merged:
            mhw[a:b+1,j,i]=True
        ncell+=len(merged)>0
print('cells with MHW',ncell, 'total mhw cell-days', mhw.sum())
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<len(active):
    if active[t]:
        s0=t
        while t<len(active) and active[t]: t+=1
        events.append((tgt[s0].isoformat(), tgt[t-1].isoformat()))
    else: t+=1
print(events)
print('active days', active.sum(), 'hot cell-days', hot.sum())
os.makedirs('/tmp/out',exist_ok=True)
np.save('/tmp/out/mhw.npy',mhw); 
json.dump({'events':events},open('/tmp/out/ev.json','w'))
'''
open('/tmp/mhw.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/mhw.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-3000:])