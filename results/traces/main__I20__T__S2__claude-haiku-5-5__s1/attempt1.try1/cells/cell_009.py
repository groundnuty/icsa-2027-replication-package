
code = r'''
import numpy as np, pandas as pd, json, os, warnings
warnings.filterwarnings('ignore')
sub=np.load('/tmp/w/sub.npy'); T=pd.DatetimeIndex(pd.read_csv('/tmp/w/T.csv',index_col=0,parse_dates=True).index)
lat=np.load('/tmp/w/lat.npy'); lon=np.load('/tmp/w/lon.npy')
def isleap(y): return (y%4==0 and y%100!=0) or y%400==0
def doy(ts):
    std=ts.dayofyear
    if (not isleap(ts.year)) and std>=60: return std+1
    return std
DOY=np.array([doy(t) for t in T])
pos={t:i for i,t in enumerate(T)}
bases=pd.date_range('1992-01-01','2002-12-31')
pools={}
for b in bases:
    d=doy(b)
    if d==60: continue
    for k in range(-5,6):
        t=b+pd.Timedelta(days=k)
        if t in pos: pools.setdefault(d,[]).append(pos[t])
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for d in range(1,367):
    if d==60: continue
    ids=sorted(set(pools[d])); vals=sub[ids]
    thr[d]=np.nanpercentile(vals,90,axis=0,method='hazen')
    clim[d]=np.nanmean(vals,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(a):
    x=a[1:367]; out=np.empty_like(x)
    for i in range(366):
        ii=[(i+k)%366 for k in range(-15,16)]
        out[i]=np.mean(x[ii],axis=0)
    r=np.full_like(a,np.nan); r[1:367]=out; return r
thrS=smooth(thr); climS=smooth(clim)
tm=(T>=pd.Timestamp('2012-06-01'))&(T<=pd.Timestamp('2012-08-31'))
tgt_idx=np.where(tm)[0]; tgt=sub[tgt_idx]
sea=np.all(np.isfinite(tgt),axis=0)
print('sea cells', sea.sum(), 'target days', len(tgt_idx), 'pool sizes', len(set(pools[1])), len(set(pools[366])))
print('sea cells with nan threshold', np.sum(sea & ~np.isfinite(thrS[1:367]).all(axis=0)))
D=DOY[tgt_idx]; nT=len(tgt_idx)
hot=np.zeros((nT,60,60),bool)
for j in range(nT): hot[j]=(tgt[j]>=thrS[D[j]])
hot &= sea[None]
mhw=np.zeros_like(hot)
for a in range(60):
    for b in range(60):
        if not sea[a,b]: continue
        h=hot[:,a,b]; segs=[]; j=0
        while j<nT:
            if h[j]:
                k=j
                while k<nT and h[k]: k+=1
                if k-j>=5: segs.append([j,k-1])
                j=k
            else: j+=1
        merged=[]
        for s in segs:
            if merged and (s[0]-merged[-1][1]-1) in (1,2): merged[-1][1]=s[1]
            else: merged.append(list(s))
        for s,e in merged: mhw[s:e+1,a,b]=True
active=mhw.any(axis=(1,2))
events=[]; j=0
while j<nT:
    if active[j]:
        k=j
        while k<nT and active[k]: k+=1
        events.append((T[tgt_idx[j]],T[tgt_idx[k-1]])); j=k
    else: j+=1
print('events', len(events))
for e in events: print(e[0].date(), e[1].date())
print('mhw cell-days', int(mhw.sum()), 'active days', int(active.sum()), 'hot cell-days', int(hot.sum()))
np.save('/tmp/w/mhw.npy',mhw); np.save('/tmp/w/tgt_idx.npy',tgt_idx)
json.dump({'events':[{'onset':str(a.date()),'end':str(b.date())} for a,b in events]}, open('/tmp/w/events.json','w'))
'''
open('/tmp/w/run.py','w').write(code)
import subprocess
print(subprocess.run(['python','/tmp/w/run.py'],capture_output=True,text=True))
