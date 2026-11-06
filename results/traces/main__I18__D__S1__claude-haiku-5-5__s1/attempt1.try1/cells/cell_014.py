code = r'''
import numpy as np, datetime as dt, json, os, warnings
from scipy.ndimage import convolve1d
warnings.filterwarnings('ignore')
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5):
    days.append(d); d+=dt.timedelta(1)
d=dt.date(2010,6,1)
while d<=dt.date(2010,8,31):
    days.append(d); d+=dt.timedelta(1)
S=[];LAT=None;LON=None
for dd in days:
    z=np.load(f'/work/cache/{dd.strftime("%Y%m%d")}.npz')
    S.append(z['sst'])
    if LAT is None: LAT=z['lat']; LON=z['lon']
    else: assert np.array_equal(LAT,z['lat']) and np.array_equal(LON,z['lon'])
S=np.stack(S); N=len(days)
def doy(dd): return dt.date(2000,dd.month,dd.day).timetuple().tm_yday
D=np.array([doy(x) for x in days])
base_mask=np.array([dt.date(1992,1,1)<=x<=dt.date(2002,12,31) for x in days])
targ_mask=np.array([dt.date(2010,6,1)<=x<=dt.date(2010,8,31) for x in days])
nE=N-int(targ_mask.sum())
Sx=S[:nE]; Dx=D[:nE]; Bx=base_mask[:nE]
thr=np.full((367,60,60),np.nan); clim=np.full((367,60,60),np.nan)
for dd in range(1,367):
    if dd==60: continue
    c=(Bx&(Dx==dd)).astype(float)
    if c.sum()==0: continue
    pm=convolve1d(c,np.ones(11),mode='constant',cval=0)>0
    pool=Sx[pm]
    thr[dd]=np.nanpercentile(pool,90,axis=0,method='hazen')
    clim[dd]=np.nanmean(pool,axis=0)
thr[60]=(thr[59]+thr[61])/2; clim[60]=(clim[59]+clim[61])/2
def smooth(arr):
    out=np.zeros_like(arr)
    for k in range(-15,16):
        out+=np.roll(arr,-k,axis=0)
    return out/31.0
thrS=np.full((367,60,60),np.nan); thrS[1:]=smooth(thr[1:])
climS=np.full((367,60,60),np.nan); climS[1:]=smooth(clim[1:])
tgt=S[nE:]; tdays=[x for x,m in zip(days,targ_mask) if m]; tD=D[targ_mask]
sea=np.all(np.isfinite(tgt),axis=0)
print('sea cells',sea.sum(),'nan thr sea',(sea & np.isnan(thrS[tD]).any(axis=0)).sum())
print('thr 60 check', np.nanmax(np.abs(thrS[60]-(thrS[59]+thrS[61])/2)) if True else 0)
T=thrS[tD]  # (92,60,60) threshold per target day
hot=(tgt>=T)&sea[None]
hot=hot & np.isfinite(T)
nt=hot.shape[0]
mhw=np.zeros((nt,60,60),bool)
gapinfo=[]
for i in range(60):
    for j in range(60):
        if not sea[i,j]: continue
        h=hot[:,i,j]
        # runs
        runs=[]; t=0
        while t<nt:
            if h[t]:
                s=t
                while t<nt and h[t]: t+=1
                if t-s>=5: runs.append([s,t-1])
            else: t+=1
        if not runs: continue
        ev=[runs[0]]
        for r in runs[1:]:
            gap=r[0]-ev[-1][1]-1
            if gap in (1,2):
                ev[-1]=[ev[-1][0], r[1]]
                gapinfo.append(gap)
            else: ev.append(r)
        for s,e in ev: mhw[s:e+1,i,j]=True
active=mhw.any(axis=(1,2))
events=[]; t=0
while t<nt:
    if active[t]:
        s=t
        while t<nt and active[t]: t+=1
        events.append((tdays[s],tdays[t-1]))
    else: t+=1
print('active days',active.sum(),'events',[(a.isoformat(),b.isoformat()) for a,b in events])
print('gap joins',len(gapinfo), 'mhw cell-days', mhw.sum())
np.savez('/work/result.npz', mhw=mhw, tdays=np.array([x.isoformat() for x in tdays]), lat=LAT, lon=LON)
json.dump({'events':[(a.isoformat(),b.isoformat()) for a,b in events]}, open('/work/events.json','w'))
'''
open('/work/run.py','w').write(code)
import subprocess
r=subprocess.run(['python','/work/run.py'],capture_output=True,text=True); print(r.stdout[-4000:], r.stderr[-3000:])