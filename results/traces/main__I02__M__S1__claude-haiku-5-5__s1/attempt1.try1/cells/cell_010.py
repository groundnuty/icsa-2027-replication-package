
script = r'''
import numpy as np, datetime as dt, json, os, warnings
import xarray as xr
warnings.filterwarnings('ignore')
d='/data/icsa2027_data_20261101T090944Z/s1z'
z=np.load('/tmp/sub.npz'); A=z['A']; days=[dt.date.fromisoformat(s) for s in z['days']]; LAT=z['lat']; LON=z['lon']
def doy2(t):
    return (dt.date(2000,t.month,t.day)-dt.date(2000,1,1)).days+1
assert doy2(dt.date(2003,2,28))==59 and doy2(dt.date(2003,3,1))==61 and doy2(dt.date(2003,12,31))==366 and doy2(dt.date(2004,6,1))==153
idx={t:i for i,t in enumerate(days)}
baseDates=[]; s=dt.date(1992,1,1)
while s<=dt.date(2002,12,31): baseDates.append(s); s+=dt.timedelta(1)
bydoy={}
for b in baseDates: bydoy.setdefault(doy2(b),[]).append(b)
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for k in range(1,367):
    if k==60: continue
    ds_=set()
    for b in bydoy.get(k,[]):
        for off in range(-5,6): ds_.add(b+dt.timedelta(off))
    ids=sorted(idx[t] for t in ds_ if t in idx)
    P=A[ids]
    thr[k]=np.nanquantile(P,0.9,axis=0,method='hazen')
    clim[k]=np.nanmean(P,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth366(X3):
    arr=X3[1:367]; out=np.empty_like(arr)
    for i in range(366):
        ids=[(i+o)%366 for o in range(-15,16)]
        out[i]=np.mean(arr[ids],axis=0)
    res=np.full_like(X3,np.nan); res[1:367]=out; return res
thrS=smooth366(thr)
tgt=[i for i,t in enumerate(days) if dt.date(2004,6,1)<=t<=dt.date(2004,8,31)]
T=A[tgt]; tdays=[days[i] for i in tgt]; nT=len(tgt)
sea=np.all(np.isfinite(T),axis=0)
print('sea cells',sea.sum(),'of',sea.size,'ntarget',nT)
doys=np.array([doy2(t) for t in tdays])
TH=thrS[doys]
hot=(T>=TH)&np.isfinite(TH)&sea[None]
def runs(b):
    out=[]; n=len(b); i=0
    while i<n:
        if b[i]:
            j=i
            while j+1<n and b[j+1]: j+=1
            out.append((i,j)); i=j+1
        else: i+=1
    return out
mhw=np.zeros((nT,60,60),bool)
for y in range(60):
    for x in range(60):
        if not sea[y,x]: continue
        r=[(a,b) for a,b in runs(hot[:,y,x]) if b-a+1>=5]
        if not r: continue
        groups=[list(r[0])]
        for a,b in r[1:]:
            if a-groups[-1][1]-1<=2: groups[-1][1]=b
            else: groups.append([a,b])
        for a,b in groups: mhw[a:b+1,y,x]=True
active=mhw.any(axis=(1,2))
events=[]; i=0
while i<nT:
    if active[i]:
        j=i
        while j+1<nT and active[j+1]: j+=1
        events.append({"onset":tdays[i].isoformat(),"end":tdays[j].isoformat()}); i=j+1
    else: i+=1
print(events)
print('active days',int(active.sum()),'mhw cell-days',int(mhw.sum()), 'hot cell-days', int(hot.sum()))
print('max SST sea', float(np.nanmax(T[:,sea])), 'min thr', float(np.nanmin(TH[:,sea])))
os.makedirs('output',exist_ok=True)
import netCDF4
'''
open('/tmp/run.py','w').write(script)
import subprocess
print(subprocess.run(['python','/tmp/run.py'],capture_output=True,text=True,cwd='/tmp'))