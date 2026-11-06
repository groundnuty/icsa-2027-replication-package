code = r'''
import numpy as np, datetime as dt, json, os
from collections import defaultdict
import xarray as xr
z=np.load('/tmp/w/sst.npz'); S=z['S']; dates=[dt.date.fromisoformat(x) for x in z['dates']]; lat=z['lat']; lon=z['lon']
idx={d:i for i,d in enumerate(dates)}
def doy(d): return dt.date(2000,d.month,d.day).timetuple().tm_yday
ny,nx=S.shape[1:]
thr=np.full((367,ny,nx),np.nan); clim=np.full((367,ny,nx),np.nan)
base=[]; d=dt.date(1992,1,1)
while d<=dt.date(2002,12,31): base.append(d); d+=dt.timedelta(1)
bydoy=defaultdict(list)
for t in base:
    if t.month==2 and t.day==29: continue
    bydoy[doy(t)].append(t)
for dd in range(1,367):
    if dd==60: continue
    us=set()
    for t in bydoy.get(dd,[]):
        for k in range(-5,6): us.add(t+dt.timedelta(k))
    ii=[idx[u] for u in sorted(us) if u in idx]
    pool=S[ii]
    with np.errstate(all='ignore'):
        thr[dd]=np.nanquantile(pool,0.9,axis=0,method='hazen')
        clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(A):
    B=A[1:367]; out=np.empty_like(B)
    for i in range(366):
        ids=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(B[ids],axis=0)
    R=np.full_like(A,np.nan); R[1:367]=out; return R
thr_s=smooth(thr); clim_s=smooth(clim)
tdates=[]; d=dt.date(2005,6,1)
while d<=dt.date(2005,8,31): tdates.append(d); d+=dt.timedelta(1)
ti=[idx[d] for d in tdates]
T=S[ti]
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size,'days',len(tdates))
tdoy=np.array([doy(d) for d in tdates])
thr_t=thr_s[tdoy]
print('NaN thr on sea cells (any doy):', np.isnan(thr_s[1:][:,sea]).sum())
hot=(T>=thr_t)&sea[None]
def runs(b):
    out=[]; n=len(b); i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
mhw=np.zeros(T.shape,dtype=bool)
for y in range(ny):
    for x in range(nx):
        if not sea[y,x]: continue
        ev=[r for r in runs(hot[:,y,x]) if r[1]-r[0]+1>=5]
        merged=[]
        for r in ev:
            if merged and r[0]-merged[-1][1]-1<=2: merged[-1]=(merged[-1][0],r[1])
            else: merged.append(r)
        for a,b_ in merged: mhw[a:b_+1,y,x]=True
active=mhw.any(axis=(1,2))
print('active days',active.sum())
evs=runs(active)
events=[{"onset":tdates[a].isoformat(),"end":tdates[b_].isoformat()} for a,b_ in evs]
print(events)
os.makedirs('/tmp/w/out',exist_ok=True)
os.makedirs('/mnt/output',exist_ok=True)
'''
open('/tmp/w/run.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/w/run.py'],capture_output=True,text=True); print(r.stdout, r.stderr[-2000:])