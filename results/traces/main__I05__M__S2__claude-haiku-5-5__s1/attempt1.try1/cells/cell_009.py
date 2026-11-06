
script = r'''
import numpy as np, pandas as pd, warnings, json, os
warnings.filterwarnings('ignore')
z=np.load('/tmp/w/cache.npz')
bv=z['b'].astype(np.float64); bt=pd.DatetimeIndex(z['bt']); tv=z['t'].astype(np.float64); tt=pd.DatetimeIndex(z['tt'])
lat=z['lat']; lon=z['lon']
def doy(ts): return np.array([pd.Timestamp(2000,d.month,d.day).day_of_year for d in ts])
bdoy=doy(bt)
ntime=bv.shape[0]
flat=bv.reshape(ntime,-1)
inbase=(bt>=pd.Timestamp('1992-01-01'))&(bt<=pd.Timestamp('2002-12-31'))
C=flat.shape[1]
thr=np.full((367,C),np.nan); clim=np.full((367,C),np.nan)
for d in range(1,367):
    if d==60: continue
    xs=np.where(inbase&(bdoy==d))[0]
    if len(xs)==0: continue
    sel=sorted({i+k for i in xs for k in range(-5,6) if 0<=i+k<ntime})
    pool=flat[sel]
    thr[d]=np.nanquantile(pool,0.9,axis=0,method='hazen')
    clim[d]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    a=a[1:367]; out=np.empty_like(a)
    for i in range(366):
        out[i]=a[[(i+k)%366 for k in range(-15,16)]].mean(axis=0)
    return out
thrS=smooth(thr); climS=smooth(clim)
sea=np.isfinite(tv).all(axis=0).reshape(-1)
tdoy=doy(tt)
T=tv.reshape(len(tt),-1)
thrT=thrS[tdoy-1]
hot=(T>=thrT)&sea[None,:]
nd=hot.shape[0]
mhw=np.zeros_like(hot)
for c in np.where(sea)[0]:
    h=hot[:,c]; runs=[]; i=0
    while i<nd:
        if h[i]:
            j=i
            while j<nd and h[j]: j+=1
            if j-i>=5: runs.append([i,j-1])
            i=j
        else: i+=1
    merged=[]
    for r in runs:
        gap=r[0]-merged[-1][1]-1 if merged else None
        if merged and 1<=gap<=2: merged[-1][1]=r[1]
        else: merged.append(list(r))
    for s,e in merged: mhw[s:e+1,c]=True
act=mhw.any(axis=1)
events=[]; i=0
while i<nd:
    if act[i]:
        j=i
        while j<nd and act[j]: j+=1
        events.append((tt[i].date().isoformat(), tt[j-1].date().isoformat())); i=j
    else: i+=1
'''
open('/tmp/w/run.py','w').write(script)
diag = r'''
exec(open('/tmp/w/run.py').read())
m=(bt.month>=6)&(bt.month<=8)&inbase
print('events',events)
print('baseline JJA mean SST sea:', np.nanmean(flat[m][:,sea]), ' 2021 JJA:', np.nanmean(T[:,sea]))
print('hot frac', hot.sum()/(sea.sum()*nd))
print('mean thrS-climS summer', np.nanmean((thrS-climS)[150:240][:,sea]))
c=np.where(sea)[0][100]
print('cell thr doy170', thrS[169,c], 'clim', climS[169,c], 'obs 2021 range', T[:,c].min(), T[:,c].max())
print('baseline JJA cell pct90', np.nanquantile(flat[m][:,c],0.9), 'mean', np.nanmean(flat[m][:,c]))
print('2021 Jun-Aug cell mean', T[:,c].mean(), 'thrT first days', thrT[:3,c], T[:3,c])
'''
open('/tmp/w/diag.py','w').write(diag)
import subprocess
print(subprocess.run(['python','/tmp/w/diag.py'],capture_output=True,text=True))
